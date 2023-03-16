import loguru

from constant.chatgpt_config import ChatGPTConfig
from util.chatgpt import ChatGPT

logger = loguru.logger


class ChatGPTAgent:
    def __init__(self):
        self.chatgpt_config: ChatGPTConfig = ChatGPTConfig()
        self.chatgpt: ChatGPT = ChatGPT(self.chatgpt_config)
        self.conversation_id: str = None
        self.init_prompt: str = "Let's supposeYou are a experienced and knowledgeable tester about RESTful API. You need do everything to help me write test cases."
        self.sequence_generation_prompt: str = """
        You are given a list of RESTful APIs in the format of OpenAPI/Swagger. The format is `api_name: method_name: path (api_summary) (api_description)`. For example, `API1: POST: /api/v1/users (Create a user) (Create a user with the given user name)`. and the empty string `` will be used if the value is empty. You need to write test cases for these RESTful APIs. You need to know the dependencies between parameters in different RESTful APIs. You need to tell me the dependencies between parameters in different RESTful APIs. For example, if I give you two RESTful APIs, one is POST /api/v1/users, and the other is POST /api/v1/users/{user_id}/friends, you need to tell me that the parameter user_id in the second API is the parameter user_id in the first API. Your test cases should call mutiple RESTful APIs in the correct order. The test case should follow the format of `TEST_CASE: api_name -> api_name -> api_name -> ... -> api_name`. For example, `TEST_CASE: API1 -> API2 -> API3 -> API4 -> API5`. Each line is a test case. Please list more than 20 test cases.
        The list of RESTful APIs is as follows:
        """

    def start_conversation(self):
        logger.info("start conversation")
        text, self.conversation_id = self.chatgpt.send_message(self.init_prompt)
        logger.info(f"conversation id: {self.conversation_id}")
        logger.info(f"chatgpt response: {text}")
