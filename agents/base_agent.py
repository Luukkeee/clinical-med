from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Base class for all clinical pipeline agents."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_log = []

    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context and return updated context."""
        pass

    def log(self, message: str):
        self.execution_log.append({"agent": self.name, "message": message})

    def get_logs(self):
        return self.execution_log.copy()

    def clear_logs(self):
        self.execution_log.clear()
