import collections
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import loguru

from model.method import Method
from model.parameter import Parameter, ParameterAttribute
from model.request_response import Request, Response

logger = loguru.logger


class RuntimeDictionary:
    """
    This class is used to store the runtime values of the parameters.
    """

    def __init__(self, fuzzer: "Fuzzer"):
        self.fuzzer: "Fuzzer" = fuzzer
        self.method_set: Set[Method] = set()
        self.method_to_parameter_attribute_map: Dict[
            Method, Set[ParameterAttribute]
        ] = {}
        self.method_to_response_list_map: Dict[Method, List[Response]] = {}
        self.method_parameter_attribute_to_value_map: Dict[
            Tuple[Method, ParameterAttribute], List[Any]
        ] = {}
        self.fifo_length: int = 20

    def add_response(self, response: Response):
        if response.status_code >= 300:
            return

        method: Method = response.method
        self.method_set.add(method)

        # add response to response list
        if method not in self.method_to_response_list_map:
            self.method_to_response_list_map[method] = collections.deque(
                maxlen=self.fifo_length
            )
        self.method_to_response_list_map[method].append(response)

        # add parameter attribute to parameter attribute set
        if method not in self.method_to_parameter_attribute_map:
            self.method_to_parameter_attribute_map[method] = set()
        for parameter_attribute in response.response_body_value_map.values():
            self.method_to_parameter_attribute_map[method].add(parameter_attribute)
            logger.info(
                f"Found new parameter attribute: {parameter_attribute} on {method}"
            )

        # add parameter attribute to value map
        for parameter_attribute in response.response_body_value_map.values():
            method_parameter_tuple = (method, parameter_attribute)
            if (
                method_parameter_tuple
                not in self.method_parameter_attribute_to_value_map
            ):
                self.method_parameter_attribute_to_value_map[
                    method_parameter_tuple
                ] = collections.deque(maxlen=self.fifo_length)
            for value in parameter_attribute.get_parameter_value():
                self.method_parameter_attribute_to_value_map[
                    method_parameter_tuple
                ].append(value)
