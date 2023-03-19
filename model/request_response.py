import dataclasses
from typing import Any, Dict, List, Tuple

from model.method import Method
from model.parameter import Parameter, ParameterAttribute


@dataclasses.dataclass
class Request:
    method: Method = None
    request_attribute_value_map: Dict[ParameterAttribute, Any] = dataclasses.field(
        default_factory=dict
    )
    params: Dict[str, Any] = dataclasses.field(default_factory=dict)
    data: Dict[str, Any] = dataclasses.field(default_factory=dict)
    url: str = None
    headers: Dict[str, Any] = dataclasses.field(default_factory=dict)
    files: Dict[str, Any] = dataclasses.field(default_factory=dict)
    form_data: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Response:
    status_code: int = None
    method: Method = None
    request: Request = None
    response_raw_body: Dict[str, Any] = dataclasses.field(default_factory=dict)
    response_attribute_value_map: Dict[ParameterAttribute, Any] = dataclasses.field(
        default_factory=dict
    )
