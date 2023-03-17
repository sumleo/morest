import dataclasses
from typing import Any, Dict, List, Tuple

from model.method import Method
from model.parameter import Parameter, ParameterAttribute


@dataclasses.dataclass
class Response:
    status_code: int = None
    method: Method = None
    request_raw_body: Dict[str, Any] = dataclasses.field(default_factory=dict)
    response_raw_body: Dict[str, Any] = dataclasses.field(default_factory=dict)
    request_attribute_value_map: Dict[ParameterAttribute, Any] = dataclasses.field(
        default_factory=dict
    )
    response_attribute_value_map: Dict[ParameterAttribute, Any] = dataclasses.field(
        default_factory=dict
    )
