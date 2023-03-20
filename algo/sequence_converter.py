import os.path
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin

import loguru
import requests

from algo.data_generator import DataGenerator
from algo.runtime_dictionary import RuntimeDictionary, RuntimeValueResult
from constant.api import ResponseCustomizedStatusCode
from model.method import Method
from model.parameter import Parameter, ParameterAttribute
from model.request_response import Request, Response
from model.sequence import Sequence
from util.request_builder import build_request

logger = loguru.logger


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
        generated_value_tuple_list: List[Tuple[Parameter, Any]] = []
        runtime_dictionary_result_list: List[RuntimeValueResult] = []
        for parameter_name in method.request_parameter:
            parameter: Parameter = method.request_parameter[parameter_name]
            # initialize data generator
            data_generator: DataGenerator = DataGenerator(
                self, method_index, method, sequence, last_response, response_list
            )
            value = data_generator.generate_value(parameter.parameter)

            # if value is SKIP_SYMBOL, skip this parameter
            if value == DataGenerator.SKIP_SYMBOL:
                continue

            generated_value_tuple_list.append((parameter, value))
            runtime_dictionary_result_list.extend(
                data_generator.runtime_value_result_list
            )

        return generated_value_tuple_list, runtime_dictionary_result_list

    def _do_request(self, method: Method, request: Request) -> Response:
        request_actor = getattr(self.request_session, method.method_type.value)
        url = self.fuzzer.config.url + request.url
        response: Response = Response()
        response.request = request
        response.method = method

        # do request
        try:
            raw_response: requests.Response = request_actor(
                url,
                params=request.params,
                data=request.form_data,
                json=request.data,
                headers=request.headers,
                files=request.files,
                allow_redirects=False,
                timeout=30,
            )
        except requests.exceptions.ReadTimeout as err:
            logger.error(err)
            response.status_code = ResponseCustomizedStatusCode.TIMEOUT.value
        except Exception as e:  # probably an encoding error
            raise e
        else:
            try:
                response.parse_response(raw_response)
            except Exception as e:  # returned value format not correct
                logger.error(f"Error when parsing response: {e}, {raw_response.text}")
        return response

    def convert(self, sequence: Sequence) -> Sequence:
        # renew session
        self._new_session()

        last_response: Response = None
        response_list: List[Response] = []

        # generate value for each parameter in the sequence methods' parameters
        for method_index, method in enumerate(sequence.method_sequence):
            # generate random data
            generated_value, runtime_dictionary_result = self._generate_random_data(
                method_index, method, sequence, response_list, last_response
            )

            # assemble data
            request: Request = build_request(method, generated_value)

            # do response
            response = self._do_request(method, request)

            # add to runtime dictionary
            self.runtime_dictionary.add_response(response)

            # update dependency success count
            for runtime_dictionary_result_item in runtime_dictionary_result:
                if 200 <= response.status_code < 300:
                    runtime_dictionary_result_item.dependency.update(1)
                else:
                    runtime_dictionary_result_item.dependency.update(-1)

            # call analysis function
            self.fuzzer._on_request_response(sequence, request, response)

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
