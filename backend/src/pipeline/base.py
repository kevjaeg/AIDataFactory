from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageResult:
    """Result from a pipeline stage execution."""
    success: bool
    data: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class PipelineStage(ABC):
    """Base class for all pipeline stages."""

    stage_name: str

    @abstractmethod
    async def process(self, input_data: Any, config: dict) -> StageResult:
        """Process input data and return results."""
        ...

    @abstractmethod
    async def validate_input(self, input_data: Any) -> bool:
        """Validate input before processing."""
        ...
