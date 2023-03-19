from typing import Dict, List, Tuple

import loguru

from analysis.base_analysis import Analysis
from model.method import Method
from model.operation_dependency_graph import OperationDependencyGraph
from model.request_response import Request, Response
from model.sequence import Sequence

logger = loguru.logger


class StatisticAnalysis(Analysis):
    name = "statistic_analysis"

    def on_init(self, odg_graph: OperationDependencyGraph):
        self.method_list: List[Method] = list(odg_graph.method_list)
        self.method_request_count: Dict[Method, int] = {
            method: 0 for method in self.method_list
        }
        self.status_code_count: Dict[int, int] = {}
        self.total_success_method_set: set = set()
        self.total_failed_method_set: set = set()
        self.total_success_count: int = 0
        self.total_request_count: int = 0
        self.total_method_count: int = len(self.method_list)

    def on_request_response(self, sequence, request, response):
        status_code = response.status_code
        if status_code not in self.status_code_count:
            self.status_code_count[status_code] = 0
        self.status_code_count[status_code] += 1

        if 200 <= response.status_code < 300:
            self.total_success_count += 1
            self.total_success_method_set.add(request.method)

        if 600 > response.status_code >= 500:
            self.total_failed_method_set.add(request.method)

        self.total_request_count += 1

    def on_iteration_end(self):
        total_method_success_rate: float = (
            len(self.total_success_method_set) / self.total_method_count
        )
        total_method_failed_rate: float = (
            len(self.total_failed_method_set) / self.total_method_count
        )
        total_validate_rate: float = self.total_success_count / self.total_request_count

        logger.info(
            f"Total method success rate: {total_method_success_rate} ({len(self.total_success_method_set)} / {self.total_method_count})"
        )
        logger.info(
            f"Total method failed rate: {total_method_failed_rate} ({len(self.total_failed_method_set)} / {self.total_method_count})"
        )
        logger.info(
            f"Total validate rate: {total_validate_rate} ({self.total_success_count} / {self.total_request_count})"
        )

        for status_code in self.status_code_count:
            logger.info(
                f"Status code {status_code} count: {self.status_code_count[status_code]}, rate: {self.status_code_count[status_code] / self.total_request_count}"
            )

        # list methods which are neither success nor failed
        invalid_method_set = (
            set(self.method_list)
            - self.total_success_method_set
            - self.total_failed_method_set
        )
        logger.info(f"Total invalid method count: {len(invalid_method_set)}")
        for method in invalid_method_set:
            logger.info(f"Method {method} is neither success nor failed")

    def on_end(self):
        pass
