from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from .models import Assignment


class MessageType(str, Enum):
    CFP = "CFP"            # Call For Proposals
    PROPOSE = "PROPOSE"    # Agent proposes resource & slot
    ACCEPT = "ACCEPT"      # Coordinator accepts & commits proposal
    REFUSE = "REFUSE"      # Agent refuses (no slot available)
    DISRUPT = "DISRUPT"    # Disruption / Delay event notification
    REPAIR = "REPAIR"      # Request to repair schedule downstream


@dataclass(slots=True)
class Message:
    sender: str
    receiver: str
    msg_type: MessageType
    flight_id: str
    resource_id: str = ""
    start: int = 0
    end: int = 0
    details: str = ""

    def __str__(self) -> str:
        res = f" ({self.resource_id})" if self.resource_id else ""
        time_str = f" [{self.start}, {self.end}]" if self.start or self.end else ""
        extra = f" - {self.details}" if self.details else ""
        return f"[{self.msg_type.value}] {self.sender} -> {self.receiver}: Flight {self.flight_id}{res}{time_str}{extra}"


@dataclass(slots=True)
class Proposal:
    agent: str
    flight_id: str
    resource_id: str
    start: int
    end: int
    score: tuple[int, int, str] = (0, 0, "")


@dataclass(slots=True)
class Commit:
    agent: str
    flight_id: str
    resource_id: str
    start: int
    end: int

    def to_assignment(self) -> Assignment:
        return Assignment(self.flight_id, self.resource_id, self.start, self.end)


@dataclass(slots=True)
class RepairNotice:
    flight_id: str
    reason: str


class MessageLogger:
    """Stores and formats CNP negotiation message logs."""
    def __init__(self) -> None:
        self.logs: List[Message] = []

    def log(self, message: Message) -> None:
        self.logs.append(message)

    def clear(self) -> None:
        self.logs.clear()

    def render(self) -> str:
        return "\n".join(str(msg) for msg in self.logs)
