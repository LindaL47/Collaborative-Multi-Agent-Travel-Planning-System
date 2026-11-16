"""Pydantic A2A schemas for the Hotel Booking Agent."""

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
    if not isinstance(value, str):
        raise ValueError("Destination code must be a string")
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
    """Supported A2A task types for the hotel agent."""

    HOTEL_SEARCH = "hotel_search"


class TaskStatus(str, Enum):
    """Lifecycle statuses returned by sub-agents to the orchestrator."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_CLARIFICATION = "needs_clarification"


class RoomType(str, Enum):
    """Supported room types.

    The orchestrator defaults to a standard room unless the user requests otherwise.
    """

    STANDARD = "standard"
    DELUXE = "deluxe"
    SUITE = "suite"
    FAMILY = "family"


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
    receiver_agent_id: Literal["hotel-agent"] = Field(default="hotel-agent", description="Logical receiving agent id.")
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

    agent_id: Literal["hotel-agent"] = Field(default="hotel-agent", description="Logical responding agent id.")
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


class HotelSearchParameters(BaseModel):
    """Structured parameters accepted by the Hotel Booking Agent."""

    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA city code.")
    check_in_date: date = Field(..., description="Hotel check-in date.")
    check_out_date: date = Field(..., description="Hotel check-out date.")
    guests: int = Field(default=1, ge=1, le=9, description="Number of guests.")
    room_type: RoomType = Field(default=RoomType.STANDARD, description="Preferred room type.")
    location_preference: Optional[str] = Field(default=None, description="Area/landmark preference.")

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)

    @field_validator("destination", mode="before")
    @classmethod
    def normalize_destination(cls, value: str) -> str:
        return normalize_city_code(value)

    @field_validator("room_type", mode="before")
    @classmethod
    def normalize_room_type(cls, value: str) -> str:
        if value is None:
            return value
        if isinstance(value, RoomType):
            return value.value
        cleaned = str(value).strip().lower().replace("-", " ").replace("_", " ")
        aliases = {
            "standard": RoomType.STANDARD.value,
            "regular": RoomType.STANDARD.value,
            "classic": RoomType.STANDARD.value,
            "deluxe": RoomType.DELUXE.value,
            "double": RoomType.DELUXE.value,
            "queen": RoomType.DELUXE.value,
            "suite": RoomType.SUITE.value,
            "junior suite": RoomType.SUITE.value,
            "family": RoomType.FAMILY.value,
            "family room": RoomType.FAMILY.value,
        }
        return aliases.get(cleaned, str(value).strip().lower())

    @field_validator("location_preference", mode="before")
    @classmethod
    def normalize_location_preference(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_dates(self) -> "HotelSearchParameters":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("Check-out date must be after check-in date.")
        return self

    @property
    def nights(self) -> int:
        """Return the number of hotel nights."""
        return (self.check_out_date - self.check_in_date).days


class HotelTaskRequest(BaseModel):
    """A2A task request sent from the orchestrator to the Hotel Booking Agent."""

    task_id: str = Field(default_factory=new_task_id, description="UUID string.")
    task_type: TaskType = Field(default=TaskType.HOTEL_SEARCH, description="A2A task type.")
    session_id: str = Field(..., description="Conversation/session UUID string.")
    parameters: HotelSearchParameters
    metadata: A2ARequestMetadata = Field(default_factory=A2ARequestMetadata)

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)

    @field_validator("task_id", "session_id")
    @classmethod
    def validate_uuid_string(cls, value: str) -> str:
        return str(UUID(str(value)))

    @model_validator(mode="after")
    def validate_task_type(self) -> "HotelTaskRequest":
        if self.task_type != TaskType.HOTEL_SEARCH.value:
            raise ValueError("Hotel agent only accepts hotel_search tasks.")
        return self


class HotelOption(BaseModel):
    """A realistic mock hotel option returned by the hotel search graph."""

    hotel_name: str
    destination: str
    city_name: str
    star_rating: float = Field(..., ge=1, le=5)
    area: str
    price_per_night_usd: int = Field(..., ge=1)
    amenities: List[str] = Field(default_factory=list)
    distance_from_landmark: str
    room_type: RoomType = Field(default=RoomType.STANDARD)
    refundable: bool = True
    # Optional presentation data for the mock dashboard. These are simulated,
    # and are never represented as live hotel reviews, offers, or locations.
    review_rating: Optional[float] = Field(default=None, ge=1, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)
    original_price_per_night_usd: Optional[int] = Field(default=None, ge=1)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    illustration_key: Optional[str] = None

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)


class HotelTaskResponse(BaseModel):
    """A2A response returned by the Hotel Booking Agent to the orchestrator."""

    task_id: str
    status: TaskStatus
    results: List[HotelOption] = Field(default_factory=list)
    clarification_needed: Optional[str] = None
    error: Optional[str] = None
    metadata: A2AResponseMetadata = Field(default_factory=A2AResponseMetadata)

    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_assignment=True, str_strip_whitespace=True)

    @field_validator("task_id")
    @classmethod
    def validate_uuid_string(cls, value: str) -> str:
        return str(UUID(str(value)))

    @model_validator(mode="after")
    def validate_status_payload(self) -> "HotelTaskResponse":
        self.metadata.result_count = len(self.results)
        if self.status == TaskStatus.SUCCESS.value:
            if not self.results:
                raise ValueError("Successful hotel responses must include results.")
            if self.clarification_needed or self.error:
                raise ValueError("Successful hotel responses cannot include clarification or error fields.")
        elif self.status == TaskStatus.PARTIAL.value:
            if not self.results or not self.clarification_needed or self.error:
                raise ValueError("Partial hotel responses require results and clarification without an error.")
        elif self.status == TaskStatus.NEEDS_CLARIFICATION.value:
            if self.results or not self.clarification_needed or self.error:
                raise ValueError("Clarification responses require clarification_needed and no results or error.")
        elif self.status == TaskStatus.FAILED.value:
            if self.results or self.clarification_needed or not self.error:
                raise ValueError("Failed responses require an error and no results or clarification.")
        return self

    @classmethod
    def success(cls, task_id: str, results: List[HotelOption]) -> "HotelTaskResponse":
        return cls(task_id=task_id, status=TaskStatus.SUCCESS, results=results)

    @classmethod
    def partial(cls, task_id: str, results: List[HotelOption], clarification: str) -> "HotelTaskResponse":
        return cls(
            task_id=task_id,
            status=TaskStatus.PARTIAL,
            results=results,
            clarification_needed=clarification,
        )

    @classmethod
    def needs_clarification(cls, task_id: str, clarification: str) -> "HotelTaskResponse":
        return cls(
            task_id=task_id,
            status=TaskStatus.NEEDS_CLARIFICATION,
            results=[],
            clarification_needed=clarification,
        )

    @classmethod
    def failed(cls, task_id: str, error: str) -> "HotelTaskResponse":
        return cls(task_id=task_id, status=TaskStatus.FAILED, results=[], error=error)
