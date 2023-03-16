from typing import Dict, List, Tuple

import loguru

from algo.chatgpt_agent import ChatGPTAgent
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

    def setup(self):
        self.sequence_list = self.graph.generate_sequence()
        logger.info(f"generated {len(self.sequence_list)} sequences")

    def fuzz(self):
        pass
