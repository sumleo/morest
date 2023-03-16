import dataclasses


@dataclasses.dataclass
class FuzzerConfig:
    time_budget: float = 600
