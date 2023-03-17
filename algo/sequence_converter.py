from typing import Any, Dict, List, Tuple

import requests

from algo.data_generator import DataGenerator
from algo.runtime_dictionary import RuntimeDictionary
from model.method import Method
from model.parameter import Parameter, ParameterAttribute
from model.response import Response
from model.sequence import Sequence


class SequenceConverter:
    def __init__(self, fuzzer: "Fuzzer"):
        self.fuzzer: "Fuzzer" = fuzzer
        self.runtime_dictionary: RuntimeDictionary = RuntimeDictionary(fuzzer)

        # initialize session
        self.request_session: requests.Session = None
        self._new_session()

    def _new_session(self):
        self.request_session = requests.Session()

    def _generate_random_data(
        self,
        method_index: int,
        method: Method,
        sequence: Sequence,
        response_list: List[Response],
        last_response: Response,
    ) -> Any:
        for parameter_name in method.request_parameter:
            parameter: Parameter = method.request_parameter[parameter_name]
            # initialize data generator
            data_generator: DataGenerator = DataGenerator(
                self, method_index, method, sequence, last_response, response_list
            )
            value = data_generator.generate_value(parameter.parameter)

    def convert(self, sequence: Sequence) -> Sequence:
        # renew session
        self._new_session()

        last_response: Response = None
        response_list: List[Response] = []

        # generate value for each parameter in the sequence methods' parameters
        for method_index, method in enumerate(sequence.method_sequence):
            self._generate_random_data(
                method_index, method, sequence, response_list, last_response
            )

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
