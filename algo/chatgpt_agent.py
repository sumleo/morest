import ast
import copy
import dataclasses
import json
import queue
import re
import threading
from typing import Any, Callable, Dict, List, Set, Tuple

import loguru

from constant.chatgpt_config import ChatGPTCommandType, ChatGPTConfig
from model.method import Method
from model.request_response import Request
from util.chatgpt import ChatGPT

logger = loguru.logger


@dataclasses.dataclass
class ChatGPTCommand:
    command: ChatGPTCommandType = None

    def execute(self, agent: "ChatGPTAgent") -> Any:
        pass


@dataclasses.dataclass
class CommandResponse:
    command: ChatGPTCommand = None
    result: Any = None


@dataclasses.dataclass
class InitializeCommand(ChatGPTCommand):
    command: ChatGPTCommandType = ChatGPTCommandType.INITIALIZE

    def execute(self, agent: "ChatGPTAgent"):
        agent.start_conversation()
        return True


@dataclasses.dataclass
class GenerateSequenceFromMethodListCommand(ChatGPTCommand):
    command: ChatGPTCommandType = ChatGPTCommandType.GENERATE_SEQUENCE
    method_list: List[Method] = dataclasses.field(default_factory=list)

    def execute(self, agent: "ChatGPTAgent"):
        raw_sequence = agent._generate_sequence_from_method_list(self.method_list)
        if raw_sequence is None:
            return None
        return agent.parse_raw_sequence(raw_sequence)


@dataclasses.dataclass
class GenerateSequenceForFailedMethodListCommand(ChatGPTCommand):
    command: ChatGPTCommandType = ChatGPTCommandType.GENERATE_SEQUENCE
    success_method_list: List[Method] = dataclasses.field(default_factory=list)
    failed_method_list: List[Method] = dataclasses.field(default_factory=list)

    def execute(self, agent: "ChatGPTAgent"):
        raw_sequence = agent._generate_sequence_from_method_list(self.method_list)
        if raw_sequence is None:
            return None
        return agent.parse_raw_sequence(raw_sequence)


@dataclasses.dataclass
class GeneratePlainInstanceFromMethodDocCommand(ChatGPTCommand):
    command: ChatGPTCommandType = ChatGPTCommandType.GENERATE_PLAIN_INSTANCE
    method_list: List[Method] = dataclasses.field(default_factory=list)

    def execute(self, agent: "ChatGPTAgent"):
        raw_response = agent._generate_request_instance_by_openapi_document(
            self.method_list
        )
        if raw_response is None:
            return None
        return agent._parse_request_instance_from_chatgpt_result(raw_response)


class ChatGPTAgent:
    def __init__(self, fuzzer: "Fuzzer"):
        self.fuzzer: "Fuzzer" = fuzzer
        self.chatgpt_config: ChatGPTConfig = ChatGPTConfig()
        self.chatgpt: ChatGPT = ChatGPT(self.chatgpt_config)
        self.conversation_id: str = None
        self.has_pending_method_instance_generation: bool = False
        self.init_prompt: str = """
As an experienced and knowledgeable tester of RESTful APIs, your task is to thoroughly test the API using the OpenAPI/Swagger documents provided. You are responsible for identifying any missing or incorrect information in the documentation, fixing the issues, and generating test cases that cover all the functionalities of the API. Additionally, you need to identify parameter dependencies in different API/Operation/Method(s) and update the OpenAPI/Swagger documents to reflect the dependencies.

To complete this task, you should use your knowledge of testing, software engineering, and other relevant factors to develop a testing strategy that covers all aspects of the API. This should include functional testing, boundary testing, security testing, and performance testing. You will also need to execute the test cases using various tools such as Postman or a custom testing framework and log the results.

As part of the testing process, you should review the OpenAPI/Swagger documents to ensure that they accurately reflect the API's structure, endpoints, and parameters. If any issues are found, you should update the documentation to fix them. Additionally, you should identify parameter dependencies in different API/Operation/Method(s) and document them in the OpenAPI/Swagger documents.

Overall, your goal is to ensure that the RESTful API is thoroughly tested and that the OpenAPI/Swagger documents are accurate and up-to-date. For this message, you just need to reply `OK` to continue.
        """
        self.sequence_generation_prompt: str = """
You have been provided with a set of RESTful APIs in the OpenAPI/Swagger format. Each API is represented by the following format: api_name: method_name: path (api_summary) (api_description). For example, an API named create_user with a POST method and the path /api/v1/users, along with a summary of "Create a user" and a description of "Create a user with the given user name" would be described as create_user: POST: /api/v1/users (Create a user) (Create a user with the given user name).

Your task is to generate a series of valid test cases for these APIs, where each test case should call multiple APIs but not exceed 5 APIs. You must guarantee that the test cases are logically correct and do not violate any constraints or requirements specified in the API documentation.

To begin, please produce at least 20 test cases using the following format:

```
TEST_CASE: API1 -> API2 -> API3 -> ... -> API5
```

The format should be followed strictly.

As you generate your test cases, consider the various HTTP methods that are supported by the APIs, including GET, POST, PUT, and DELETE. Additionally, consider any possible status codes that can be returned by each API, as well as any expected error messages. Finally, be sure to validate any input parameters, such as query parameters, headers, and request bodies, to ensure that the APIs are behaving as expected.

Please note that your test cases must be logically sound, complete and free of errors, as they will be used to test the functionality of the RESTful APIs.

You must not include any conclusion, explaination and purpose.

You must only output testcases.

The testcases must follow the format above.

The APIs are listed below:

        """

        self.batch_input_prompt: str = """
        Due to token limit, you just need to reply `OK` to continue until I ask you questions.
        """

        self.generate_instance_chunk_size = 8

        self.plain_instance_generation_prompt: str = """
You have been provided with the OpenAPI/Swagger documentation for several RESTful APIs. Your task is to create a request instance for each API, following the format below, which will be used as arguments for Python's requests library:

```json
{
    "path": <path>,
    "params": <params>,
    "form_data": <form_data>,
    "json_data": <json_data>,
    "headers": <headers>,
    "files": <files>
    "operation_id": <operation_id>
}
```

Construct individual JSON schema request instances for each API, taking into account ChatGPT's output limitations. Each request instance should begin with REQUEST_INSTANCE: in one line, followed by the JSON schema, such as REQUEST_INSTANCE: {"path": {"petId": 1}}. Avoid potential parameter value conflict in these request instances. For instance, you can not create two users with same `user_id`.

Note that the different fields in the request instance are optional and may not be present for all APIs. Here's a brief description of each field:

path: (optional) Path variables of the request.
params: (optional) Dictionary, list of tuples, or bytes to send in the query string for the request.
form_data: (optional) Dictionary, list of tuples, bytes, or file-like object to send in the body of the request as form-data.
json_data: (optional) A JSON serializable Python object to send in the body of the request.
headers: (optional) Dictionary of HTTP headers to send with the request.
files: (optional) Dictionary of 'name': file-like-objects (or {'name': file-tuple}) for multipart encoding upload. The file-like objects must use `"<file-placeholder>"` as the place holder.
operation_id: (required) The operation ID in OpenAPI/Swagger documentation.

Please do not include any explanation or descriptions in your request instances. 

Please generate valid API request instances for the following APIs, using the provided API documentation as a reference. Analyze the descriptions, requirements, and constraints for each API to ensure the request instances adhere to the specified guidelines. 

Each request instance must a valid json in one line.


        """
        self.command_queue: queue.Queue = queue.Queue()
        self.command_response_queue: queue.Queue = queue.Queue()
        self.command_response_handler_map: Dict[
            ChatGPTCommandType, Callable[[CommandResponse], None]
        ] = {
            ChatGPTCommandType.INITIALIZE: lambda response: logger.info(
                "initialize chatgpt"
            ),
            ChatGPTCommandType.GENERATE_SEQUENCE: self._handle_generate_sequence_response,
            ChatGPTCommandType.GENERATE_PLAIN_INSTANCE: self._handle_generate_plain_instance_response,
        }
        self.worker_thread: threading.Thread = threading.Thread(
            target=self._execute_command_worker,
            daemon=True,
            name="ChatGPTAgentWorker",
            args=(self.command_queue, self.command_response_queue),
        )
        # start worker thread
        self.worker_thread.start()

    def init_chatgpt(self):
        logger.info("initialize chatgpt")
        initialize_command = InitializeCommand()
        self.execute_command(initialize_command)

    def generate_sequence_from_method_list(self, method_list: List[Method]) -> str:
        logger.info("generate sequence from method list")
        generate_sequence_command = GenerateSequenceFromMethodListCommand(
            method_list=method_list
        )
        self.execute_command(generate_sequence_command)

    def execute_command(self, command: ChatGPTCommand):
        self.command_queue.put(command)

    def _execute_command_worker(
        self, command_queue: queue.Queue, command_response_queue: queue.Queue
    ):
        logger.info("start command worker")
        has_task = False
        while True:
            if has_task:
                continue

            # Wait for a task to become available
            command = command_queue.get()

            # if debug mode, skip command
            if self.chatgpt_config.is_debugging:
                continue

            # Indicate that a task is available
            has_task = True

            # Execute time-consuming task
            raw_result = command.execute(self)

            # Generate command response
            command_response = CommandResponse(command=command, result=raw_result)

            # Notify main thread with result
            command_response_queue.put(command_response)

            # Indicate that the task is complete
            has_task = False

    def start_conversation(self):
        logger.info("start conversation")
        text, self.conversation_id = self.chatgpt.send_new_message(self.init_prompt)
        logger.info(f"conversation id: {self.conversation_id}")
        logger.info(f"chatgpt response: {text}")

    def _generate_sequence_from_method_list(self, method_list: List[Method]) -> str:
        logger.info("generate sequence from method list")
        prompt: str = self.sequence_generation_prompt
        for method in method_list:
            prompt += f"{method.operation_id}: {method.method_type.value}: {method.method_path} ({method.summary}) ({method.description})\n"
        result = self.chatgpt.send_message(prompt, self.conversation_id)
        return result

    def _generate_sequence_for_failed_method_list(
        self, success_method_list: List[Method], failed_method_list: List[Method]
    ) -> str:
        logger.info("generate sequence for failed method list")
        prompt: str = self.sequence_generation_prompt
        for method in method_list:
            prompt += f"{method.operation_id}: {method.method_type.value}: {method.method_path} ({method.summary}) ({method.description})\n"
        result = self.chatgpt.send_message(prompt, self.conversation_id)
        return result

    def parse_raw_sequence(self, raw_text: str) -> List[List[str]]:
        test_case_list: List[List[str]] = []
        for line in raw_text.splitlines():
            if "TEST_CASE:" in line:
                token_list = line.split("TEST_CASE: ")[1].split(" -> ")
                token_list = [token.strip() for token in token_list]
                test_case_list.append(token_list)
        return test_case_list

    def _generate_request_instance_by_openapi_document(self, method_list: List[Method]):
        """
        Generate a request instance following the OpenAPI document.

        :param api_document:
        :return:
        """
        api_document = ""
        for method in method_list:
            raw_body = copy.deepcopy(method.method_raw_body)
            if "responses" in raw_body:
                del raw_body["responses"]
            api_fragment = {method.method_path: raw_body}
            api_document += f"{api_fragment}\n"
        prompt: str = f"""
        {self.plain_instance_generation_prompt}
        
        {api_document}
        
        """
        result = self.chatgpt.send_message(prompt, self.conversation_id)
        return result

    def _generate_request_instance_sequence_by_openapi_document(
        self, method_list: List[Method]
    ):
        """
        Generate a request instance following the OpenAPI document.

        :param api_document:
        :return:
        """
        api_document = ""
        for method in method_list:
            api_document += f"{method.method_raw_body}\n"

        prompt: str = f"""
         Generate an request instance for a test case following the OpenAPI document for each method in the test case:

         {api_document}

         The generated request instance is formatted as separate JSON data for each method. Use the attribute `query` to store the query parameters, `header` to store the header parameters, `path` to store the path parameters, `body` to store the body parameters, and `formData` to store the form data parameters. The generated instance must be in the same order as the methods in the test case and follow the potential parameter dependencies between the methods in the test case.


         """
        result = self.chatgpt.send_message(prompt, self.conversation_id)
        return result

    def generate_request_instance_by_openapi_document(self, method_list: List[Method]):
        if self.conversation_id is None:
            return
        if self.has_pending_method_instance_generation:
            return
        chunk_method_list = []
        for method in method_list:
            chunk_method_list.append(method)
            self.has_pending_method_instance_generation = True
            if len(chunk_method_list) >= self.generate_instance_chunk_size:
                command = GeneratePlainInstanceFromMethodDocCommand()
                command.method_list = chunk_method_list
                self.command_queue.put(command)
                chunk_method_list = []

        if len(chunk_method_list) > 0:
            command = GeneratePlainInstanceFromMethodDocCommand()
            command.method_list = chunk_method_list
            self.command_queue.put(command)

    def generate_test_case_and_instance_containing_never_success_method(
        self, method_list: List[Method]
    ):
        if self.conversation_id is None:
            return
        if self.has_pending_method_instance_generation:
            return

    def command_response_handler(self, response: CommandResponse):
        handler = self.command_response_handler_map.get(response.command.command)
        handler(response)

    def _parse_request_instance_from_chatgpt_result(self, result: str) -> List[str]:
        instance_list = []
        for line in result.splitlines():
            if "REQUEST_INSTANCE:" in line:
                instance = line.split("REQUEST_INSTANCE:")[1]
                instance_list.append(instance)
        return instance_list

    def _handle_generate_plain_instance_response(self, response: CommandResponse):
        instance_list = response.result
        self.has_pending_method_instance_generation = False
        if instance_list is None:
            logger.error("Failed to generate instance")
            return
        for instance_list_item in instance_list:
            try:
                value_dict: dict = json.loads(instance_list_item)
            except Exception as ex:
                logger.error(f"Failed to parse instance: {instance_list_item}")
                continue
            self._update_file_like_object_from_instance(value_dict)
            operation_id: str = value_dict.get("operation_id", None)
            method: Method = self.fuzzer.operation_id_to_method_map[operation_id]
            url = method.method_path
            path_variable_dict = value_dict.get("path", {})
            if isinstance(path_variable_dict, dict):
                for key, value in path_variable_dict.items():
                    url = url.replace("{" + key + "}", str(value))
            request = Request()
            request.method = method
            request.url = url
            request.params = value_dict.get("params", None)
            request.form_data = value_dict.get("form_data", None)
            request.data = value_dict.get("json_data", None)
            request.headers = value_dict.get("headers", None)
            files = value_dict.get("files", None)
            request.files = files
            self.fuzzer.pending_request_list.append(request)

    def _update_file_like_object_from_instance(self, instance: Any):
        placeholder = "<file-placeholder>"
        if isinstance(instance, dict):
            for key, value in instance.items():
                if value == placeholder:
                    instance[key] = open("./assets/smallest.jpg", "rb")
                else:
                    self._update_file_like_object_from_instance(value)
        elif isinstance(instance, list):
            for item in instance:
                self._update_file_like_object_from_instance(item)

    def _handle_generate_sequence_response(self, response: CommandResponse):
        raw_sequence_list = response.result
        if raw_sequence_list is None:
            logger.error("Failed to generate sequence")
            return
        sequence_list = self.fuzzer.graph.generate_sequence_by_chatgpt(
            raw_sequence_list
        )
        self.fuzzer.pending_sequence_list = sequence_list

    def process_chatgpt_result(self):
        while not self.command_response_queue.empty():
            response = self.command_response_queue.get()
            self.command_response_handler(response)
