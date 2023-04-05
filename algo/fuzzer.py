import datetime
import pathlib
import time
from typing import Dict, List, Set, Tuple

import loguru

from algo.chatgpt_agent import ChatGPTAgent
from algo.sequence_converter import SequenceConverter
from analysis.base_analysis import Analysis
from analysis.statistic_analysis import StatisticAnalysis
from constant.data_generation_config import DataGenerationConfig
from constant.fuzzer_config import FuzzerConfig
from model.method import Method
from model.operation_dependency_graph import OperationDependencyGraph
from model.request_response import Request, Response
from model.sequence import Sequence

logger = loguru.logger

ANALYSIS = [StatisticAnalysis]


class Fuzzer:
    def __init__(self, graph: OperationDependencyGraph, config: FuzzerConfig):
        self.begin_time: float = time.time()
        self.start_time_str: str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.output_dir: pathlib.Path = (
            pathlib.Path(config.output_dir) / self.start_time_str
        )
        self.graph: OperationDependencyGraph = graph
        self.config: FuzzerConfig = config
        self.time_budget: float = config.time_budget
        # self.chatgpt_agent: ChatGPTAgent = ChatGPTAgent(self)
        self.sequence_list: List[Sequence] = []
        self.sequence_converter: SequenceConverter = SequenceConverter(self)
        self.data_generation_config: DataGenerationConfig = DataGenerationConfig()
        self.analysis_list: List[Analysis] = []
        self.success_method_set: Set[Method] = set()
        self.failed_method_set: Set[Method] = set()
        self.never_success_method_set: Set[Method] = set()
        self.pending_request_list: List[Request] = []
        self.operation_id_to_method_map: Dict[str, Method] = {}
        self.pending_sequence_list: List[Sequence] = []
        self.single_method_sequence_list: List[Sequence] = []

    def setup(self):
        logger.info("Fuzzer setup")
        self._init_analysis()
        # self.chatgpt_agent.init_chatgpt()
        # self.chatgpt_agent.generate_sequence_from_method_list(self.graph.method_list)
        self.single_method_sequence_list = self.graph._generate_single_method_sequence()
        self.sequence_list = (
            self.graph.generate_sequence() + self.single_method_sequence_list
        )
        self.pending_sequence_list = self.sequence_list.copy()

        for method in self.graph.method_list:
            self.operation_id_to_method_map[method.operation_id] = method

        logger.info(f"generated {len(self.sequence_list)} sequences")

    def _init_analysis(self):
        for analysis in ANALYSIS:
            analyzer = analysis()
            analyzer.on_init(self)
            self.analysis_list.append(analyzer)

    def _on_iteration_end(self):
        for analysis in self.analysis_list:
            analysis.on_iteration_end()

    def _on_request_response(
        self, sequence: Sequence, request: Request, response: Response
    ):
        for analysis in self.analysis_list:
            analysis.on_request_response(sequence, request, response)

    def warm_up(self):
        logger.info("warmup")

        # convert sequence to request
        for _ in range(self.config.warm_up_times):
            for sequence in self.single_method_sequence_list:
                self.sequence_converter.convert(sequence)
            self._on_iteration_end()

    def fuzz(self):
        converter = self.sequence_converter

        while self.begin_time + self.time_budget > time.time():
            # convert sequence to request
            for sequence in self.sequence_list:
                converter.convert(sequence)

            # process chatgpt result
            # self.chatgpt_agent.process_chatgpt_result()

            # execute pending request
            # for request in self.pending_request_list:
            #     converter.request_chatgpt_single_instance(request)
            self.pending_request_list.clear()

            # handlers for each iteration
            self._on_iteration_end()

            # handle the case that all methods are never success
            # self.chatgpt_agent.generate_request_instance_by_openapi_document(
            #     list(self.never_success_method_set)
            # )

            # update sequence list
            if self.pending_sequence_list == 0:
                continue
            self.sequence_list += self.pending_sequence_list
            self.pending_sequence_list.clear()
