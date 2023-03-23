# -*- coding: utf-8 -*-

import dataclasses
import json
import re
import time
from typing import Any, Dict, List, Tuple
from uuid import uuid1

import loguru
import requests

from constant.chatgpt_config import ChatGPTConfig

logger = loguru.logger


@dataclasses.dataclass
class Message:
    ask_id: str = None
    ask: dict = None
    answer: dict = None
    answer_id: str = None
    request_start_timestamp: float = None
    request_end_timestamp: float = None
    time_escaped: float = None


@dataclasses.dataclass
class Conversation:
    conversation_id: str = None
    message_list: List[Message] = dataclasses.field(default_factory=list)

    def __hash__(self):
        return hash(self.conversation_id)

    def __eq__(self, other):
        if not isinstance(other, Conversation):
            return False
        return self.conversation_id == other.conversation_id


class ChatGPT:
    def __init__(self, config: ChatGPTConfig):
        self.config = config
        self.model = config.model
        self.proxies = {"https": ""}
        self._puid = config._puid
        self.cf_clearance = config.cf_clearance
        self.session_token = config.session_token
        # conversation_id: message_id
        self.conversation_dict: Dict[str, Conversation] = {}
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

    def _parse_message_raw_output(self, response: requests.Response):
        # 解析消息返回结果
        last_line = None
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if len(decoded_line) == 12:
                    break
                if "data:" in decoded_line:
                    last_line = decoded_line
        result = json.loads(last_line[5:])
        return result

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
        start_time = time.time()
        message: Message = Message()
        message.ask_id = message_id
        message.ask = data
        message.request_start_timestamp = start_time
        r = requests.post(
            url, headers=self.headers, json=data, proxies=self.proxies, stream=True
        )
        if r.status_code != 200:
            # 发送消息阻塞时等待20秒从新发送
            logger.error(r.text)
            return None, None

        # parsing result
        result = self._parse_message_raw_output(r)
        text = "\n".join(result["message"]["content"]["parts"])
        conversation_id = result["conversation_id"]
        answer_id = result["message"]["id"]

        end_time = time.time()
        message.answer_id = answer_id
        message.answer = result
        message.request_end_timestamp = end_time
        message.time_escaped = end_time - start_time
        conversation: Conversation = Conversation()
        conversation.conversation_id = conversation_id
        conversation.message_list.append(message)

        self.conversation_dict[conversation_id] = conversation
        return text, conversation_id

    def send_message(self, message, conversation_id):
        # 指定会话窗口发送连续对话消息
        logger.info(f"send_message")
        url = "https://chat.openai.com/backend-api/conversation"

        # 获取会话窗口最新消息id
        if conversation_id not in self.conversation_dict:
            logger.info(f"conversation_id: {conversation_id}")
            message_id = self.get_latest_message_id(conversation_id)
            logger.info(f"message_id: {message_id}")
        else:
            message_id = (
                self.conversation_dict[conversation_id].message_list[-1].answer_id
            )

        new_message_id = str(uuid1())
        data = {
            "action": "next",
            "messages": [
                {
                    "id": new_message_id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [message]},
                }
            ],
            "conversation_id": conversation_id,
            "parent_message_id": message_id,
            "model": self.model,
        }

        start_time = time.time()
        message: Message = Message()
        message.ask_id = new_message_id
        message.ask = data
        message.request_start_timestamp = start_time

        r = requests.post(
            url, headers=self.headers, json=data, proxies=self.proxies, stream=True
        )
        if r.status_code != 200:
            # 发送消息阻塞时等待20秒从新发送
            logger.warning(f"chatgpt failed: {r.text}")
            return None, None
            # parsing result

        result = self._parse_message_raw_output(r)
        text = "\n".join(result["message"]["content"]["parts"])
        conversation_id = result["conversation_id"]
        answer_id = result["message"]["id"]

        end_time = time.time()
        message.answer_id = answer_id
        message.answer = result
        message.request_end_timestamp = end_time
        message.time_escaped = end_time - start_time
        conversation: Conversation = self.conversation_dict[conversation_id]
        conversation.message_list.append(message)
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
        if conversation_id in self.conversation_dict:
            del self.conversation_dict[conversation_id]

        if r.status_code == 200:
            return True
        else:
            logger.error("Failed to delete conversation")
            return False

    def extract_code_fragments(self, text):
        code_fragments = re.findall(r"```(.*?)```", text, re.DOTALL)
        return code_fragments
