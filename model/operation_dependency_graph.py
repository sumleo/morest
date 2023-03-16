import dataclasses
from typing import Dict, List, Tuple

from model.api import API
from model.match_rule.base_rule import Rule
from model.match_rule.substr_rule import SubStringRule
from model.method import Method
from model.parameter_dependency import (InContextParameterDependency,
                                        ParameterDependency)
from model.sequence import Sequence


@dataclasses.dataclass
class Edge:
    producer: Method = None
    consumer: Method = None
    parameter_dependency_list: List[ParameterDependency] = dataclasses.field(
        default_factory=list
    )


class OperationDependencyGraph:
    def __init__(self, apis: List[API]):
        self.api_list: List[API] = apis
        self.method_list: List[Method] = []
        self.edge_list: List[Edge] = []
        self.rule_list: List[Rule] = [SubStringRule]
        self.producer_consumer_map: Dict[Method, List[Method]] = {}
        self.consumer_producer_map: Dict[Method, List[Method]] = {}
        self.producer_consumer_edge_map: Dict[Method, List[Edge]] = {}
        self.consumer_producer_edge_map: Dict[Method, List[Edge]] = {}
        self.producer_consumer_to_edge_map: Dict[Tuple[Method, Method], Edge] = {}

    def build(self):
        # extract methods from apis
        for api in self.api_list:
            for method in api.method_dict.values():
                self.method_list.append(method)

        # build producer-consumer map
        for producer in self.method_list:
            for consumer in self.method_list:
                if producer == consumer:
                    continue
                for rule in self.rule_list:
                    if rule.has_parameter_dependency(producer, consumer):
                        parameter_dependency_list = rule.build_parameter_dependency(
                            producer, consumer
                        )
                        if producer not in self.producer_consumer_map:
                            self.producer_consumer_map[producer] = []
                        self.producer_consumer_map[producer].append(consumer)
                        if consumer not in self.consumer_producer_map:
                            self.consumer_producer_map[consumer] = []
                        self.consumer_producer_map[consumer].append(producer)
                        edge = Edge(producer, consumer, parameter_dependency_list)
                        self.edge_list.append(edge)
                        if producer not in self.producer_consumer_edge_map:
                            self.producer_consumer_edge_map[producer] = []
                        self.producer_consumer_edge_map[producer].append(edge)
                        if consumer not in self.consumer_producer_edge_map:
                            self.consumer_producer_edge_map[consumer] = []
                        self.consumer_producer_edge_map[consumer].append(edge)
                        self.producer_consumer_to_edge_map[(producer, consumer)] = edge
                        break

    def generate_sequence(self) -> List[Sequence]:
        """
        Recursive generate sequence by producer-consumer map

        :return: List[Sequence]
        """
        sequence_list = []
        for producer in self.producer_consumer_map:
            sequence_list += self._generate_sequence(producer, Sequence())
        return sequence_list

    def _generate_sequence(
        self, producer: Method, sequence: Sequence
    ) -> List[Sequence]:
        """
        Recursive generate sequence by producer-consumer map

        :param producer: Method
        :param sequence: Sequence
        :return: List[Sequence]
        """
        sequence_list = []

        sequence.add_method(producer)

        # it is a leaf node
        if producer not in self.producer_consumer_map:
            return [sequence.copy()]
        producer_index = sequence.method_sequence.index(producer)

        for consumer in self.producer_consumer_map[producer]:
            if consumer in sequence.method_sequence:
                sequence_list.append(sequence.copy())
                continue

            seq = sequence.copy()
            dependency: InContextParameterDependency = InContextParameterDependency(
                producer=producer, consumer=consumer
            )
            for parameter_dependency in self.producer_consumer_to_edge_map[
                (producer, consumer)
            ].parameter_dependency_list:
                dependency.add_parameter_dependency(parameter_dependency)

            dependency.producer_index = producer_index
            dependency.consumer_index = producer_index + 1
            seq.add_parameter_dependency(dependency)
            sequence_list += self._generate_sequence(consumer, seq.copy())
        return sequence_list

    def generate_prompt(self):
        background = """
I am a new tester of RESTful APIs. I want to test a brunch of RESTful APIs. I want to know the dependencies between parameters in different RESTful APIs to write test cases.
I will give you a list of RESTful APIs. You need to tell me the dependencies between parameters in different RESTful APIs.
For example, if I give you two RESTful APIs, one is POST /api/v1/users, and the other is POST /api/v1/users/{user_id}/friends, you need to tell me that the parameter user_id in the second API is the parameter user_id in the first API.
First, I will give you a list of RESTful APIs by the this format: `API_NAME: METHOD_NAME: PATH (API_SUMMARY) (API_DESCRIPTION)` as following. For example, `API1: POST: /api/v1/users (Create a user) (Create a user with the given user name)`. and the empty string `` will be used if the value is empty.
"""

        api_description = ""

        for method in self.method_list:
            api_description += f"{method.operation_id}: {str.upper(method.method_type.name)}: {method.method_path} ({method.summary}) ({method.description})\n"
        prompt = background + api_description
        prompt += "Please give me all the posible dependencies between parameters in different RESTful APIs. The format is `PRODUCER_API_NAME: CONSUMER_API_NAME` as following. For example, `API1: API2`. and the `None` will be used if the value is empty. Each dependency is in one line. Please list all of the dependecies.\n"
        prompt += """

Secondly, I will give you a list of dependencies between parameters in different RESTful APIs by the this format: `PRODUCER_API_NAME: CONSUMER_API_NAME: PRODUCER_PARAMETER_NAME PRODUCER_PARAMETER_ATTRIBUTE_PATH (PRODUCER_PARAMETER_DESCRIPTION) -> CONSUMER_PARAMETER_NAME CONSUMER_PARAMETER_ATTRIBUTE_PATH (CONSUMER_PARAMETER_DESCRIPTION)` as following. For example, `API1: API2: user_id users.user_id (The user id) -> user_id users.user_id (The user id)`. and the `None` will be used if the value is empty.
"""
        parameter_dependency_description = ""
        count = 0
        for edge in self.edge_list:
            for parameter_dependency in edge.parameter_dependency_list:
                count += 1
                parameter_dependency_description += f"{count}. {parameter_dependency.producer.operation_id}: {parameter_dependency.consumer.operation_id}: {parameter_dependency.producer_parameter.attribute_name} {parameter_dependency.producer_parameter.attribute_path} ({parameter_dependency.producer_parameter.description}) -> {parameter_dependency.consumer_parameter.attribute_name} {parameter_dependency.consumer_parameter.attribute_path} ({parameter_dependency.consumer_parameter.description})\n"
            if count >= 20:
                break
        prompt += parameter_dependency_description
        prompt += f"""
Can you tell me the {count} dependencies listed above is correct or not? If it is correct, please tell me in "True". If it is not correct, please tell me in "False". If you don't know, please tell me in "None". Please each dependency in a line. For example, if the first dependency is correct, the second dependency is not correct, and the third dependency is correct, you need to tell me in "True", "False", "True". If you don't know the first dependency, you need to tell me in "None", "False", "True". PRODUCER_PARAMETER_DESCRIPTION and CONSUMER_PARAMETER_DESCRIPTION are optional. You should judge the correctness of the dependency by the PRODUCER_PARAMETER_NAME, PRODUCER_PARAMETER_ATTRIBUTE_PATH, CONSUMER_PARAMETER_NAME, and CONSUMER_PARAMETER_ATTRIBUTE_PATH.

"""
        return background + api_description
