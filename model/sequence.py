import copy
import dataclasses
from typing import Dict, List, Tuple

from model.method import Method
from model.parameter import Parameter, ParameterAttribute
from model.parameter_dependency import InContextParameterDependency


@dataclasses.dataclass
class Sequence:
    method_sequence: List[Method] = dataclasses.field(default_factory=list)
    parameter_dependency_list: List[InContextParameterDependency] = dataclasses.field(
        default_factory=list
    )

    def add_method(self, method: Method):
        self.method_sequence.append(method)

    def add_parameter_dependency(
        self, parameter_dependency: InContextParameterDependency
    ):
        self.parameter_dependency_list.append(parameter_dependency)

    def copy(self):
        seq = Sequence()
        seq.method_sequence = copy.deepcopy(self.method_sequence)
        seq.parameter_dependency_list = copy.deepcopy(self.parameter_dependency_list)
        return seq
