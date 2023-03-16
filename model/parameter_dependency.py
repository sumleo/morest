import dataclasses
from typing import List

from model.method import Method
from model.parameter import ParameterAttribute


@dataclasses.dataclass
class ParameterDependency:
    match_rule: str = None
    producer: Method = None
    consumer: Method = None
    producer_parameter: ParameterAttribute = None
    consumer_parameter: ParameterAttribute = None

    @property
    def signature(self):
        return f"producer: {self.producer_parameter.signature} -> consumer: {self.consumer_parameter.signature}"

    def __repr__(self):
        return self.signature


@dataclasses.dataclass
class InContextParameterDependency:
    parameter_dependency_list: List[ParameterDependency] = dataclasses.field(
        default_factory=list
    )
    producer: Method = None
    consumer: Method = None
    producer_index: int = None
    consumer_index: int = None

    @property
    def signature(self):
        return (
            f"producer({self.producer_index}): {self.producer.signature} -> "
            f"consumer({self.consumer_index}): {self.consumer.signature}\n {self.producer_parameter_dependency_list}"
        )

    @property
    def producer_parameter_dependency_list(self):
        return ", ".join(
            [
                parameter_dependency.signature
                for parameter_dependency in self.parameter_dependency_list
                if parameter_dependency.producer == self.producer
            ]
        )

    def __repr__(self):
        return self.signature

    def add_parameter_dependency(self, parameter_dependency: ParameterDependency):
        self.parameter_dependency_list.append(parameter_dependency)
