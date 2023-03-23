import dataclasses
import enum
import json


class ChatGPTCommandType(enum.Enum):
    INITIALIZE = "initialize"
    GENERATE_SEQUENCE = "generate_sequence"
    GENERATE_PLAIN_INSTANCE = "generate_plain_instance"


chatgpt_config = json.load(open("./config.json", "r"))


@dataclasses.dataclass
class ChatGPTConfig:
    model: str = chatgpt_config["model"]
    _puid: str = chatgpt_config["puid"]
    cf_clearance: str = chatgpt_config["cf_clearance"]
    session_token: str = chatgpt_config["session_token"]
    error_wait_time: float = 20
    is_debugging: bool = False
