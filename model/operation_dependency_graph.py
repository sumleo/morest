import dataclasses
from typing import Dict, List, Tuple

import loguru

from algo.chatgpt_agent import ChatGPTAgent
from model.api import API
from model.match_rule.base_rule import Rule
from model.match_rule.substr_rule import SubStringRule
from model.method import Method
from model.parameter_dependency import (InContextParameterDependency,
                                        ParameterDependency)
from model.sequence import Sequence

logger = loguru.logger


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

    def generate_sequence_by_chatgpt(self, chatgpt: ChatGPTAgent) -> List[Sequence]:
        """
        Generate sequence by chatgpt
        :param chatgpt:
        :return: List[Sequence]
        """
        sequence_list = []
        raw_response = chatgpt.generate_sequence_from_method_list(self.method_list)
        test_sequence_list = chatgpt.parse_raw_sequence(raw_response)
        for test_sequence_line in test_sequence_list:
            sequence = Sequence()
            producer = None
            for test_sequence in test_sequence_line:
                consumer = self._find_method_by_name(test_sequence)
                if consumer is None:
                    continue
                sequence.add_method(consumer)
                # check has dependency
                if (
                    producer is not None
                    and (producer, consumer) in self.producer_consumer_to_edge_map
                ):
                    dependency = InContextParameterDependency()
                    dependency.producer = producer
                    dependency.consumer = consumer
                    dependency.producer_index = sequence.method_sequence.index(producer)
                    dependency.consumer_index = sequence.method_sequence.index(consumer)
                    for parameter_dependency in self.producer_consumer_to_edge_map[
                        (producer, consumer)
                    ].parameter_dependency_list:
                        dependency.add_parameter_dependency(parameter_dependency)
                    sequence.add_parameter_dependency(dependency)
                producer = consumer
            sequence_list.append(sequence)

        sequence_list += self._generate_single_method_sequence()

        return sequence_list

    def _generate_single_method_sequence(self) -> List[Sequence]:
        """
        Generate sequence by single method
        :return: List[Sequence]
        """
        sequence_list = []
        for method in self.method_list:
            sequence = Sequence()
            sequence.add_method(method)
            sequence_list.append(sequence)
        return sequence_list

    def _find_method_by_name(self, method_name: str) -> Method:
        for method in self.method_list:
            if method.operation_id in method_name:
                return method
        return None

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
