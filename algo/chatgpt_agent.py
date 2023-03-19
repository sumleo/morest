import dataclasses
import queue
import threading
from typing import Any, Dict, List, Tuple

import loguru

from constant.chatgpt_config import ChatGPTCommandType, ChatGPTConfig
from model.method import Method
from util.chatgpt import ChatGPT

logger = loguru.logger


@dataclasses.dataclass
class ChatGPTCommand:
    command: ChatGPTCommandType = None

    def execute(self, agent: "ChatGPTAgent") -> Any:
        pass


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
        raw_sequence = agent.generate_sequence_from_method_list(self.method_list)
        return raw_sequence


@dataclasses.dataclass
class CommandResponse:
    command: ChatGPTCommand = None
    result: Any = None


class ChatGPTAgent:
    def __init__(self):
        self.chatgpt_config: ChatGPTConfig = ChatGPTConfig()
        self.chatgpt: ChatGPT = ChatGPT(self.chatgpt_config)
        self.conversation_id: str = None
        self.init_prompt: str = """
As an experienced and knowledgeable tester of RESTful APIs, your task is to thoroughly test the API using the OpenAPI/Swagger documents provided. You are responsible for identifying any missing or incorrect information in the documentation, fixing the issues, and generating test cases that cover all the functionalities of the API. Additionally, you need to identify parameter dependencies in different API/Operation/Method(s) and update the OpenAPI/Swagger documents to reflect the dependencies.

To complete this task, you should use your knowledge of testing, software engineering, and other relevant factors to develop a testing strategy that covers all aspects of the API. This should include functional testing, boundary testing, security testing, and performance testing. You will also need to execute the test cases using various tools such as Postman or a custom testing framework and log the results.

As part of the testing process, you should review the OpenAPI/Swagger documents to ensure that they accurately reflect the API's structure, endpoints, and parameters. If any issues are found, you should update the documentation to fix them. Additionally, you should identify parameter dependencies in different API/Operation/Method(s) and document them in the OpenAPI/Swagger documents.

Overall, your goal is to ensure that the RESTful API is thoroughly tested and that the OpenAPI/Swagger documents are accurate and up-to-date. For this message, you just need to reply `OK` to continue.
        """
        self.sequence_generation_prompt: str = """
        You are given a list of RESTful APIs in the format of OpenAPI/Swagger. The format is `api_name: method_name: path (api_summary) (api_description)`. For example, `API1: post: /api/v1/users (Create a user) (Create a user with the given user name)`. and the empty string `` will be used if the value is empty. You need to write test cases for these RESTful APIs. You need to know the dependencies between parameters in different RESTful APIs. You need to tell me the dependencies between parameters in different RESTful APIs. For example, if I give you two RESTful APIs, one is POST /api/v1/users, and the other is POST /api/v1/users/{user_id}/friends, you need to tell me that the parameter user_id in the second API is the parameter user_id in the first API. Your test cases should call mutiple RESTful APIs in the correct order. The test case should follow the format of `TEST_CASE: api_name -> api_name -> api_name -> ... -> api_name`. For example, `TEST_CASE: API1 -> API2 -> API3 -> API4 -> API5`. Each line is a test case. Please list more than 20 test cases.
        The list of RESTful APIs is as follows:
        """
        self.command_queue: queue.Queue = queue.Queue()
        self.command_response_queue: queue.Queue = queue.Queue()
        self.worker_thread: threading.Thread = threading.Thread(
            target=self._execute_command_worker,
            daemon=True,
            name="ChatGPTAgentWorker",
            args=(self.command_queue, self.command_response_queue),
        )
        # start worker thread
        self.worker_thread.start()

    def _init_chatgpt(self):
        logger.info("initialize chatgpt")
        initialize_command = InitializeCommand()
        self.execute_command(initialize_command)

    def execute_command(self, command: ChatGPTCommand):
        self.command_queue.put(command)

    def _execute_command_worker(
        self, command_queue: queue.Queue, command_response_queue: queue.Queue
    ):
        logger.info("start command worker")

        while True:
            # Wait for a task to become available
            command = command_queue.get()

            # Execute time-consuming task
            raw_result = command.execute(self)

            # Generate command response
            command_response = CommandResponse(command=command, result=raw_result)

            # Notify main thread with result
            command_response_queue.put(command_response)

    def start_conversation(self):
        if self.chatgpt_config.is_debugging:
            logger.info("debugging mode, skip starting conversation")
            return
        logger.info("start conversation")
        text, self.conversation_id = self.chatgpt.send_new_message(self.init_prompt)
        logger.info(f"conversation id: {self.conversation_id}")
        logger.info(f"chatgpt response: {text}")

    def generate_sequence_from_method_list(self, method_list: List[Method]) -> str:
        if self.chatgpt_config.is_debugging:
            logger.info("debugging mode, skip generating sequence")
            return """
            Here are more than 20 test cases that test different scenarios of the given RESTful APIs:

1. TEST_CASE: uploadFile -> addPet -> getOrderById
   Description: Uploads an image, adds a new pet to the store, and retrieves the order by ID.

2. TEST_CASE: addPet -> updatePet -> getPetById
   Description: Adds a new pet to the store, updates it, and retrieves the pet by ID.

3. TEST_CASE: findPetsByStatus -> updatePetWithForm -> deletePet
   Description: Finds pets by status, updates a pet with form data, and deletes the pet.

4. TEST_CASE: findPetsByTags -> getOrderById -> deleteOrder
   Description: Finds pets by tags, retrieves an order by ID, and deletes the order.

5. TEST_CASE: getPetById -> updatePet -> placeOrder
   Description: Retrieves a pet by ID, updates it, and places an order for the pet.

6. TEST_CASE: createUsersWithArrayInput -> createUsersWithListInput -> getUserByName
   Description: Creates a list of users with an array input, creates a list of users with a list input, and retrieves a user by name.

7. TEST_CASE: getUserByName -> updateUser -> deleteUser
   Description: Retrieves a user by name, updates it, and deletes it.

8. TEST_CASE: loginUser -> getInventory -> logoutUser
   Description: Logs in a user, retrieves pet inventories by status, and logs out the user.

9. TEST_CASE: createUser -> updateUser -> getUserByName
   Description: Creates a user, updates it, and retrieves it by name.

10. TEST_CASE: updatePet -> deletePet -> placeOrder -> getOrderById
   Description: Updates a pet, deletes it, places an order for a pet, and retrieves the order by ID.

11. TEST_CASE: getInventory -> addPet -> updatePetWithForm -> findPetsByTags -> deletePet
   Description: Retrieves pet inventories by status, adds a new pet to the store, updates a pet with form data, finds pets by tags, and deletes a pet.

12. TEST_CASE: findPetsByTags -> createUsersWithArrayInput -> createUsersWithListInput -> getUserByName -> updateUser -> deleteUser
   Description: Finds pets by tags, creates a list of users with an array input, creates a list of users with a list input, retrieves a user by name, updates it, and deletes it.

13. TEST_CASE: getInventory -> addPet -> createUsersWithArrayInput -> createUser -> deleteUser -> deletePet
   Description: Retrieves pet inventories by status, adds a new pet to the store, creates a list of users with an array input, creates a user, deletes the user, and deletes the pet.

14. TEST_CASE: getPetById -> updatePetWithForm -> createUsersWithListInput -> getUserByName -> updateUser -> deleteUser
   Description: Retrieves a pet by ID, updates it with form data, creates a list of users with a list input, retrieves a user by name, updates it, and deletes it.

15. TEST_CASE: createUser -> loginUser -> updateUser -> deleteUser -> logoutUser
   Description: Creates a user, logs in the user, updates it, deletes it, and logs out the user.

16. TEST_CASE: loginUser -> getUserByName -> updateUser -> logoutUser
   Description: Logs in a user, retrieves it by name, updates it, and logs out the user.

17. TEST_CASE: createUsersWithArrayInput -> createUser -> updateUser -> deleteUser -> createUsersWithListInput -> getUserByName
   Description: Creates a list of users with an array input, creates a user, updates it, deletes it, creates
            """
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

    def generate_request_instance_by_openapi_document(self, api_document: dict):
        """
        Generate a request instance following the OpenAPI document.

        :param api_document:
        :return:
        """
        prompt: str = f"""
        Generate an request instance following the OpenAPI document:
    
        {api_document}
        
        The generated request instance is formatted as a JSON data. Use the attribute `query` to store the query parameters, `header` to store the header parameters, `path` to store the path parameters, `body` to store the body parameters, and `formData` to store the form data parameters.
        
        
        """
        result = self.chatgpt.send_message(prompt, self.conversation_id)
        return result

    def generate_request_instance_sequence_by_openapi_document(
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
