from typing import Dict, List, Tuple

from algo.fuzzer import Fuzzer
from algo.runtime_dictionary import RuntimeDictionary
from algo.sequence_converter import SequenceConverter
from model.method import Method
from model.parameter import Parameter, ParameterAttribute, ParameterType
from model.parameter_dependency import (InContextParameterDependency,
                                        ParameterDependency)
from model.sequence import Sequence


class DataGenerator:
    """Data generator class."""

    def __init__(self, sequence_converter: SequenceConverter):
        self.sequence_converter: SequenceConverter = sequence_converter
        self.fuzzer: Fuzzer = sequence_converter.fuzzer
        self.runtime_dictionary: RuntimeDictionary = (
            sequence_converter.runtime_dictionary
        )
