import dataclasses


@dataclasses.dataclass
class FuzzerConfig:
    time_budget: float = 600
    warm_up_times: int = 5
