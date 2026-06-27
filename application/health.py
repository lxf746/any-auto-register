from __future__ import annotations

from infrastructure.health_runtime import HealthRuntime


class HealthService:
    def __init__(self, runtime: HealthRuntime | None = None):
        self.runtime = runtime or HealthRuntime()

    def health(self) -> dict:
        return self.runtime.health()

    def readiness(self) -> dict:
        return self.runtime.readiness()

    def pool_status(self) -> dict:
        return self.runtime.pool_status()

    def rate_limit_status(self) -> dict:
        return self.runtime.rate_limit_status()
