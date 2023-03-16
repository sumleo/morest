from model.operation_dependency_graph import OperationDependencyGraph


class Analysis:
    name: str = "base_analysis"

    def on_init(self, odg_graph: OperationDependencyGraph):
        pass
