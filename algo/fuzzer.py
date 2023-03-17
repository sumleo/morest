from typing import Dict, List, Tuple

import loguru

from algo.chatgpt_agent import ChatGPTAgent
from algo.sequence_converter import SequenceConverter
from constant.data_generation_config import DataGenerationConfig
from constant.fuzzer_config import FuzzerConfig
from model.operation_dependency_graph import OperationDependencyGraph
from model.sequence import Sequence

logger = loguru.logger


class Fuzzer:
    def __init__(self, graph: OperationDependencyGraph, config: FuzzerConfig):
        self.graph: OperationDependencyGraph = graph
        self.config: FuzzerConfig = config
        self.time_budget: float = config.time_budget
        self.chatgpt_agent: ChatGPTAgent = ChatGPTAgent()
        self.sequence_list: List[Sequence] = []
        self.sequence_converter: SequenceConverter = SequenceConverter(self)
        self.data_generation_config: DataGenerationConfig = DataGenerationConfig()

    def setup(self):
        self.chatgpt_agent.start_conversation()
        self.sequence_list = self.graph.generate_sequence_by_chatgpt(self.chatgpt_agent)
        logger.info(f"generated {len(self.sequence_list)} sequences")
        # for seq in self.sequence_list:
        #     result = self.chatgpt_agent.generate_request_instance_sequence_by_openapi_document(
        #         seq.method_sequence
        #     )
        #     logger.info([method.signature for method in seq.method_sequence])
        #     logger.info(result)

        # for method in self.graph.method_list:
        #     result = self.chatgpt_agent.generate_request_instance_by_openapi_document(method.method_raw_body)
        #     logger.info(method.signature)
        #     logger.info(result)

    def warm_up(self):
        logger.info("warmup")

        # convert sequence to request
        for _ in range(self.config.warm_up_times):
            for sequence in self.sequence_list:
                self.sequence_converter.convert(sequence)

    def _run_sequence(self, sequence: Sequence):
        logger.info("run sequence")
        self.sequence_converter.convert(sequence)

    def fuzz(self):
        pass
