from dataclasses import dataclass


@dataclass(frozen=True)
class HealthQuery:
    pass


@dataclass(frozen=True)
class ReadinessQuery:
    pass


@dataclass(frozen=True)
class AppConfigQuery:
    pass
