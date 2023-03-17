from typing import Any, Dict, List, Tuple

import requests

from algo.fuzzer import Fuzzer
from model.method import Method
from model.sequence import Sequence


class SequenceConverter:
    def __init__(self, fuzzer: Fuzzer):
        self.fuzzer: Fuzzer = fuzzer

        # initialize session
        self.request_session: requests.Session = None
        self._new_session()

    def _new_session(self):
        self.request_session = requests.Session()

    def convert(self, sequence: Sequence) -> Sequence:
        # renew session
        self._new_session()

        # generate value for each parameter in the sequence methods' parameters
        for method in sequence.method_list:
            pass

        # assemble data

        # make request

        return sequence

    def _generate_value_for_method_by_chatgpt(self, method: Method):
        generated_value_dict: Dict[str, Any] = {}
        result = (
            self.fuzzer.chatgpt_agent.generate_request_instance_by_openapi_document(
                method.method_raw_body
            )
        )
        return result
