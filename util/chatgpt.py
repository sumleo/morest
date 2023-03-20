# -*- coding: utf-8 -*-

import json
import re
import time
from uuid import uuid1

import loguru
import requests

from constant.chatgpt_config import ChatGPTConfig

logger = loguru.logger


class ChatGPT:
    def __init__(self, config: ChatGPTConfig):
        self.config = config
        self.model = config.model
        self.proxies = {"https": ""}
        self._puid = config._puid
        self.cf_clearance = config.cf_clearance
        self.session_token = config.session_token
        # conversation_id: message_id
        self.latest_message_id_dict = {}
        self.headers = dict(
            {
                "cookie": f"cf_clearance={self.cf_clearance}; _puid={self._puid}; "
                f"__Secure-next-auth.session-token={self.session_token}",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                # 'Content-Type': 'text/event-stream; charset=utf-8',
            }
        )
        self.headers["authorization"] = self.get_authorization()

    def get_authorization(self):
        url = "https://chat.openai.com/api/auth/session"
        r = requests.get(url, headers=self.headers)
        authorization = r.json()["accessToken"]
        return "Bearer " + authorization

    def get_latest_message_id(self, conversation_id):
        # 获取会话窗口最新消息id，连续对话必须
        url = f"https://chat.openai.com/backend-api/conversation/{conversation_id}"
        r = requests.get(url, headers=self.headers, proxies=self.proxies)
        return r.json()["current_node"]

    def send_new_message(self, message):
        # 发送新会话窗口消息，返回会话id
        logger.info(f"send_new_message")
        url = "https://chat.openai.com/backend-api/conversation"
        message_id = str(uuid1())
        data = {
            "action": "next",
            "messages": [
                {
                    "id": message_id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [message]},
                }
            ],
            "parent_message_id": str(uuid1()),
            "model": self.model,
        }

        r = requests.post(url, headers=self.headers, json=data, proxies=self.proxies)
        if r.status_code != 200:
            # 发送消息阻塞时等待20秒从新发送
            logger.error(r.json()["detail"])
            time.sleep(self.config.error_wait_time)
            return self.send_new_message(message)

        last_line = None

        for line in r.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if len(decoded_line) == 12:
                    break
                last_line = decoded_line

        result = json.loads(last_line[5:])
        text = "\n".join(result["message"]["content"]["parts"])
        conversation_id = result["conversation_id"]
        response_message_id = result["message"]["id"]
        self.latest_message_id_dict[conversation_id] = response_message_id
        return text, conversation_id

    def send_message(self, message, conversation_id):
        # 指定会话窗口发送连续对话消息
        logger.info(f"send_message")
        url = "https://chat.openai.com/backend-api/conversation"
        # 获取会话窗口最新消息id
        if conversation_id not in self.latest_message_id_dict:
            logger.info(f"conversation_id: {conversation_id}")
            message_id = self.get_latest_message_id(conversation_id)
            logger.info(f"message_id: {message_id}")
        else:
            message_id = self.latest_message_id_dict[conversation_id]

        data = {
            "action": "next",
            "messages": [
                {
                    "id": str(uuid1()),
                    "role": "user",
                    "content": {"content_type": "text", "parts": [message]},
                }
            ],
            "conversation_id": conversation_id,
            "parent_message_id": message_id,
            "model": self.model,
        }
        r = requests.post(url, headers=self.headers, json=data, proxies=self.proxies)
        if r.status_code != 200:
            # 发送消息阻塞时等待20秒从新发送
            logger.warning(r.json()["detail"])
            time.sleep(self.config.error_wait_time)
            return self.send_message(message, conversation_id)
        response_result = json.loads(r.text.split("data: ")[-2])
        new_message_id = response_result["message"]["id"]
        self.latest_message_id_dict[conversation_id] = new_message_id
        text = "\n".join(response_result["message"]["content"]["parts"])
        return text

    def get_conversation_history(self, limit=20, offset=0):
        # Get the conversation id in the history
        url = "https://chat.openai.com/backend-api/conversations"
        query_params = {
            "limit": limit,
            "offset": offset,
        }
        r = requests.get(
            url, headers=self.headers, params=query_params, proxies=self.proxies
        )
        if r.status_code == 200:
            json_data = r.json()
            conversations = {}
            for item in json_data["items"]:
                conversations[item["id"]] = item["title"]
            return conversations
        else:
            logger.error("Failed to retrieve history")
            return None

    def delete_conversation(self, conversation_id=None):
        # delete conversation with its uuid
        if not conversation_id:
            return
        url = f"https://chat.openai.com/backend-api/conversation/{conversation_id}"
        data = {
            "is_visible": False,
        }
        r = requests.patch(url, headers=self.headers, json=data, proxies=self.proxies)

        # delete conversation id locally
        if conversation_id in self.latest_message_id_dict:
            del self.latest_message_id_dict[conversation_id]

        if r.status_code == 200:
            return True
        else:
            logger.error("Failed to delete conversation")
            return False

    def extract_code_fragments(self, text):
        code_fragments = re.findall(r"```(.*?)```", text, re.DOTALL)
        return code_fragments


if __name__ == "__main__":
    chatgpt_config = ChatGPTConfig()
    chatgpt = ChatGPT(chatgpt_config)
    text, conversation_id = chatgpt.send_new_message(
        "I am a new tester for RESTful APIs."
    )
    result = chatgpt.send_message(
        "generate: {'post': {'tags': ['pet'], 'summary': 'uploads an image', 'description': '', 'operationId': 'uploadFile', 'consumes': ['multipart/form-data'], 'produces': ['application/json'], 'parameters': [{'name': 'petId', 'in': 'path', 'description': 'ID of pet to update', 'required': True, 'type': 'integer', 'format': 'int64'}, {'name': 'additionalMetadata', 'in': 'formData', 'description': 'Additional data to pass to server', 'required': False, 'type': 'string'}, {'name': 'file', 'in': 'formData', 'description': 'file to upload', 'required': False, 'type': 'file'}], 'responses': {'200': {'description': 'successful operation', 'schema': {'type': 'object', 'properties': {'code': {'type': 'integer', 'format': 'int32'}, 'type': {'type': 'string'}, 'message': {'type': 'string'}}}}}, 'security': [{'petstore_auth': ['write:pets', 'read:pets']}]}}",
        conversation_id,
    )
    logger.info(chatgpt.extract_code_fragments(result))
