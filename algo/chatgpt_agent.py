import ast
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
        return agent.parse_raw_sequence(raw_sequence)


@dataclasses.dataclass
class GeneratePlainInstanceFromMethodDocCommand(ChatGPTCommand):
    command: ChatGPTCommandType = ChatGPTCommandType.GENERATE_PLAIN_INSTANCE
    method_list: List[Method] = dataclasses.field(default_factory=list)

    def execute(self, agent: "ChatGPTAgent"):
        raw_response = agent._generate_request_instance_by_openapi_document(
            self.method_list
        )
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
        You are given a list of RESTful APIs in the format of OpenAPI/Swagger. Each API is defined as `api_name: method_name: path (api_summary) (api_description)`. For instance, `API1: post: /api/v1/users (Create a user) (Create a user with the given user name)`. An empty string `("")` is used if the value is empty. Your task is to write test cases for these APIs.
        Your test cases should call multiple RESTful APIs in the correct order.
        Please provide at least 20 test cases. Do not include any explanation and descriptions in your test cases. You just need to provide the test cases.  Each test case should begin with `TEST_CASE:`, following the format of `TEST_CASE: api_name -> api_name -> api_name -> ... -> api_name`, such as `TEST_CASE: API1 -> API2 -> API3 -> API4 -> API5`.
        The list of RESTful APIs is as follows:
        
        """

        self.batch_input_prompt: str = """
        Due to token limit, you just need to reply `OK` to continue until I ask you questions.
        """

        self.generate_instance_chunk_size = 5

        self.plain_instance_generation_prompt: str = """
        You are given several RESTful API in the format of OpenAPI/Swagger documentation. 
        Please provide only one request instance for each API in separate json schema sequentially, following the format below to be used as arguments of Python's libarary. `requests`:
        
        ```json
        {
            "path":<path>,
            "params": <params>,
            "form_data":<form_data>,
            "json_data":<data>,
            "headers":<headers>,
            "files":<files>,
        }
        ```
        
        path - (optional)  path variables of the request

        params – (optional) Dictionary, list of tuples or bytes to send in the query string for the Request.
        
        form_data – (optional) Dictionary, list of tuples, bytes, or file-like object to send in the body of the Request. It's in the body as form-data.
        
        json_data – (optional) A JSON serializable Python object to send in the body of the Request.
        
        headers – (optional) Dictionary of HTTP Headers to send with the Request=-=
        
        files – (optional) Dictionary of 'name': file-like-objects (or {'name': file-tuple}) for multipart encoding upload. file-tuple can be a 2-tuple ('filename', fileobj), 3-tuple ('filename', fileobj, 'content_type') or a 4-tuple ('filename', fileobj, 'content_type', custom_headers), where 'content-type' is a string defining the content type of the given file and custom_headers a dict-like object containing additional headers to add for the file.
        
        Do not include any explanation and descriptions in your request instances. You just need to provide the request instances. Each request instance should begin with `REQUEST_INSTANCE:` in one line, following the format of `REQUEST_INSTANCE: <request_instance>`, such as `REQUEST_INSTANCE: {"path":{"petId":1}}`.
        
        The RESTful API documentation is as follows:

        """
        self.command_queue: queue.Queue = queue.Queue()
        self.command_response_queue: queue.Queue = queue.Queue()
        self.command_response_handler_map: Dict[
            ChatGPTCommandType, Callable[[CommandResponse], None]
        ] = {
            ChatGPTCommandType.INITIALIZE: lambda response: logger.info(
                "initialize chatgpt"
            ),
            ChatGPTCommandType.GENERATE_SEQUENCE: lambda response: logger.info(
                "generate sequence from method list"
            ),
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

    def parse_raw_sequence(self, raw_text: str) -> List[List[str]]:
        test_case_list: List[List[str]] = []
        for line in raw_text.splitlines():
            if "TEST_CASE: " in line:
                token_list = line.split("TEST_CASE: ")[1].split(" -> ")
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
            api_fragment = {method.method_path: method.method_raw_body}
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
        for instance_list_item, method in zip(
            instance_list, response.command.method_list
        ):
            instance_list_item = instance_list_item.strip()
            pattern = r",open\((.*?)\),"
            instance_list_item = re.sub(pattern, ",233,", instance_list_item)
            pattern = r", open\((.*?)\),"
            instance_list_item = re.sub(pattern, ",233,", instance_list_item)
            value_dict: dict = ast.literal_eval(instance_list_item)
            url = method.method_path
            path_variable_dict = value_dict.get("path", {})
            for key, value in path_variable_dict.items():
                url = url.replace("{" + key + "}", str(value))
            request = Request()
            request.method = method
            request.url = url
            request.params = value_dict.get("params", None)
            request.form_data = value_dict.get("form_data", None)
            request.data = value_dict.get("json_data", None)
            request.headers = value_dict.get("headers", None)
            files = value_dict.get("files", {})
            for key, value in files.items():
                list_value = list(value)
                list_value[0] = "smallest.jpg"
                list_value[1] = open("./assets/smallest.jpg", "rb")
                files[key] = tuple(list_value)
            request.files = files
            self.fuzzer.pending_request_list.append(request)

    def process_chatgpt_result(self):
        while not self.command_response_queue.empty():
            response = self.command_response_queue.get()
            self.command_response_handler(response)
