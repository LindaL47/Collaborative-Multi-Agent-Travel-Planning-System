"""Pydantic A2A schemas for the Flight Booking Agent.

The assignment mandates an Agent-to-Agent contract between the orchestrator and
specialised agents. This module keeps the contract schema-first and validates all
flight task requests before graph execution reaches the retrieval node.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
import re
from typing import Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CITY_CODE_ALIASES: Dict[str, str] = {
    "singapore": "SIN",
    "sin": "SIN",
    "tokyo": "TYO",
    "tyo": "TYO",
    "paris": "PAR",
    "par": "PAR",
    "dubai": "DXB",
    "dxb": "DXB",
    "london": "LON",
    "lon": "LON",
    "sydney": "SYD",
    "syd": "SYD",
    "bangkok": "BKK",
    "bkk": "BKK",
    "hong kong": "HKG",
    "hkg": "HKG",
    "seoul": "SEL",
    "sel": "SEL",
    "kuala lumpur": "KUL",
    "kul": "KUL",
    "bengaluru": "BLR",
    "bangalore": "BLR",
    "blr": "BLR",
    "delhi": "DEL",
    "new delhi": "DEL",
    "del": "DEL",
    "mumbai": "BOM",
    "bombay": "BOM",
    "bom": "BOM",
    "bali": "DPS",
    "denpasar": "DPS",
    "dps": "DPS",
    "zurich": "ZRH",
    "zrh": "ZRH",
    "rome": "ROM",
    "rom": "ROM",
    "barcelona": "BCN",
    "bcn": "BCN",
    "san francisco": "SFO",
    "sfo": "SFO",
    "toronto": "YYZ",
    "yyz": "YYZ",
    "new york": "NYC",
    "nyc": "NYC",
    "mexico city": "MEX",
    "mex": "MEX",
    "reykjavik": "KEF",
    "kef": "KEF",
    "chennai": "MAA",
    "madras": "MAA",
    "maa": "MAA",
    "guwahati": "GAU",
    "gau": "GAU",
}


def normalize_city_code(value: str) -> str:
    """Normalize a city name or IATA code to the mock-data city code."""
    if value is None:
        return value
    if not isinstance(value, str):
        raise ValueError("City code must be a string")
    cleaned = re.sub(r"[^a-z\s]", " ", value.strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned in CITY_CODE_ALIASES:
        return CITY_CODE_ALIASES[cleaned]
    return value.strip().upper()


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with timezone information."""
    return datetime.now(timezone.utc).isoformat()


def new_task_id() -> str:
    """Return a UUID string for an A2A task id."""
    return str(uuid4())


class TaskType(str, Enum):
    """Supported A2A task types for the flight agent."""

    FLIGHT_SEARCH = "flight_search"


class TaskStatus(str, Enum):
    """Lifecycle statuses returned by sub-agents to the orchestrator."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_CLARIFICATION = "needs_clarification"


class CabinClass(str, Enum):
    """Supported cabin classes.

    The orchestrator defaults to economy when the user does not specify a cabin.
    """

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class A2ARequestMetadata(BaseModel):
    """Required request metadata for orchestrator-to-agent messages.

    The assignment requires metadata with requested_by and timestamp. The extra
    protocol/audit fields are optional extensions that make the A2A lifecycle
    demo-ready without removing any mandated field.
    """

    requested_by: Literal["orchestrator"] = Field(default="orchestrator", description="Logical sender id.")
    timestamp: str = Field(default_factory=utc_now_iso, description="ISO-8601 timestamp.")
    protocol_version: Literal["a2a-mock-1.0"] = Field(default="a2a-mock-1.0", description="Local A2A contract version.")
    sender_agent_id: Literal["friendly-assistant-orchestrator"] = Field(default="friendly-assistant-orchestrator", description="Logical sending agent id.")
    receiver_agent_id: Literal["flight-agent"] = Field(default="flight-agent", description="Logical receiving agent id.")
    trace_id: str = Field(default_factory=new_task_id, description="Correlation id for multi-agent tracing.")
    parent_task_id: Optional[str] = Field(default=None, description="Optional upstream task id when fan-out is used.")
    planning_source: Literal["orchestrator", "heuristic", "ollama"] = Field(default="orchestrator", description="Planner source that produced the task parameters.")

    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("A2A timestamps must include a timezone.")
        return value

    @field_validator("trace_id", "parent_task_id")
    @classmethod
    def validate_optional_uuid_string(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return str(UUID(str(value)))


class A2AResponseMetadata(BaseModel):
    """Required response metadata for agent-to-orchestrator messages."""

    agent_id: Literal["flight-agent"] = Field(default="flight-agent", description="Logical responding agent id.")
    timestamp: str = Field(default_factory=utc_now_iso, description="ISO-8601 timestamp.")
    protocol_version: Literal["a2a-mock-1.0"] = Field(default="a2a-mock-1.0", description="Local A2A contract version.")
    trace_id: str = Field(default_factory=new_task_id, description="Correlation id for multi-agent tracing.")
    result_count: int = Field(default=0, ge=0, description="Number of options returned in results.")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking warnings for the orchestrator.")

    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("A2A timestamps must include a timezone.")
        return value

    @field_validator("trace_id")
    @classmethod
    def validate_trace_uuid(cls, value: str) -> str:
        return str(UUID(str(value)))


class FlightSearchParameters(BaseModel):
    """Structured parameters accepted by the Flight Booking Agent."""

    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA city/airport code.")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA city/airport code.")
    departure_date: date = Field(..., description="Outbound travel date.")
    return_date: Optional[date] = Field(default=None, description="Inbound date for round trips.")
    return_destination: Optional[str] = Field(default=None, min_length=3, max_length=3, description="Optional open-jaw return destination; defaults to origin.")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of travellers.")
    cabin_class: CabinClass = Field(default=CabinClass.ECONOMY, description="Preferred cabin class.")

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)

    @field_validator("origin", "destination", "return_destination", mode="before")
    @classmethod
    def normalize_iata(cls, value: str) -> str:
        return normalize_city_code(value)

    @field_validator("cabin_class", mode="before")
    @classmethod
    def normalize_cabin_class(cls, value: str) -> str:
        if value is None:
            return value
        if isinstance(value, CabinClass):
            return value.value
        cleaned = str(value).strip().lower().replace("-", " ").replace("_", " ")
        aliases = {
            "economy": CabinClass.ECONOMY.value,
            "coach": CabinClass.ECONOMY.value,
            "premium economy": CabinClass.PREMIUM_ECONOMY.value,
            "premium": CabinClass.PREMIUM_ECONOMY.value,
            "business": CabinClass.BUSINESS.value,
            "business class": CabinClass.BUSINESS.value,
            "first": CabinClass.FIRST.value,
            "first class": CabinClass.FIRST.value,
        }
        return aliases.get(cleaned, str(value).strip().lower())

    @model_validator(mode="after")
    def validate_route_and_dates(self) -> "FlightSearchParameters":
        if self.origin == self.destination:
            raise ValueError("Origin and destination must be different.")
        if self.return_destination and self.return_destination == self.destination:
            raise ValueError("Return destination must differ from trip destination.")
        if self.return_date and self.return_date <= self.departure_date:
            raise ValueError("Return date must be after departure date.")
        return self

    @property
    def is_round_trip(self) -> bool:
        """Return True when the request contains an inbound date."""
        return self.return_date is not None


class FlightTaskRequest(BaseModel):
    """A2A task request sent from the orchestrator to the Flight Booking Agent."""

    task_id: str = Field(default_factory=new_task_id, description="UUID string.")
    task_type: TaskType = Field(default=TaskType.FLIGHT_SEARCH, description="A2A task type.")
    session_id: str = Field(..., description="Conversation/session UUID string.")
    parameters: FlightSearchParameters
    metadata: A2ARequestMetadata = Field(default_factory=A2ARequestMetadata)

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)

    @field_validator("task_id", "session_id")
    @classmethod
    def validate_uuid_string(cls, value: str) -> str:
        return str(UUID(str(value)))

    @model_validator(mode="after")
    def validate_task_type(self) -> "FlightTaskRequest":
        if self.task_type != TaskType.FLIGHT_SEARCH.value:
            raise ValueError("Flight agent only accepts flight_search tasks.")
        return self


class FlightOption(BaseModel):
    """A realistic mock flight option returned by the flight search graph."""

    trip_leg: str = Field(..., description="outbound or inbound.")
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_date: date
    departure_time: str
    arrival_time: str
    duration: str
    stops: int = Field(default=0, ge=0)
    cabin_class: CabinClass = Field(default=CabinClass.ECONOMY)
    price_usd: int = Field(..., ge=1)
    baggage_note: str = Field(default="1 checked bag included")

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)


class FlightTaskResponse(BaseModel):
    """A2A response returned by the Flight Booking Agent to the orchestrator."""

    task_id: str
    status: TaskStatus
    results: List[FlightOption] = Field(default_factory=list)
    clarification_needed: Optional[str] = None
    error: Optional[str] = None
    metadata: A2AResponseMetadata = Field(default_factory=A2AResponseMetadata)

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)

    @field_validator("task_id")
    @classmethod
    def validate_uuid_string(cls, value: str) -> str:
        return str(UUID(str(value)))

    @model_validator(mode="after")
    def validate_status_payload(self) -> "FlightTaskResponse":
        self.metadata.result_count = len(self.results)
        if self.status == TaskStatus.SUCCESS.value:
            if not self.results:
                raise ValueError("Successful flight responses must include results.")
            if self.clarification_needed or self.error:
                raise ValueError("Successful flight responses cannot include clarification or error fields.")
        elif self.status == TaskStatus.PARTIAL.value:
            if not self.results or not self.clarification_needed or self.error:
                raise ValueError("Partial flight responses require results and clarification without an error.")
        elif self.status == TaskStatus.NEEDS_CLARIFICATION.value:
            if self.results or not self.clarification_needed or self.error:
                raise ValueError("Clarification responses require clarification_needed and no results or error.")
        elif self.status == TaskStatus.FAILED.value:
            if self.results or self.clarification_needed or not self.error:
                raise ValueError("Failed responses require an error and no results or clarification.")
        return self

    @classmethod
    def success(cls, task_id: str, results: List[FlightOption]) -> "FlightTaskResponse":
        return cls(task_id=task_id, status=TaskStatus.SUCCESS, results=results)

    @classmethod
    def partial(cls, task_id: str, results: List[FlightOption], clarification: str) -> "FlightTaskResponse":
        return cls(
            task_id=task_id,
            status=TaskStatus.PARTIAL,
            results=results,
            clarification_needed=clarification,
        )

    @classmethod
    def needs_clarification(cls, task_id: str, clarification: str) -> "FlightTaskResponse":
        return cls(
            task_id=task_id,
            status=TaskStatus.NEEDS_CLARIFICATION,
            results=[],
            clarification_needed=clarification,
        )

    @classmethod
    def failed(cls, task_id: str, error: str) -> "FlightTaskResponse":
        return cls(task_id=task_id, status=TaskStatus.FAILED, results=[], error=error)
