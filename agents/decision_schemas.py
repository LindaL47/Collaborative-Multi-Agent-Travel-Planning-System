"""Typed option groups and A2A contracts shared by the decision agents."""

from __future__ import annotations

from typing import Generic, Literal, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agents.flight_agent.schemas import (
    A2ARequestMetadata,
    A2AResponseMetadata,
    FlightOption,
    new_task_id,
)
from agents.hotel_agent.schemas import HotelOption

DecisionStrategy = Literal["balanced", "budget", "comfort"]


class DecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FlightDecisionGroup(DecisionModel):
    group_id: str
    label: str
    options: list[FlightOption] = Field(default_factory=list)


class HotelDecisionGroup(DecisionModel):
    group_id: str
    label: str
    nights: int = Field(ge=1)
    options: list[HotelOption] = Field(default_factory=list)


class DecisionParameters(DecisionModel):
    flight_groups: list[FlightDecisionGroup] = Field(default_factory=list)
    hotel_groups: list[HotelDecisionGroup] = Field(default_factory=list)
    passengers: int = Field(default=1, ge=1, le=9)
    strategy: DecisionStrategy = "balanced"
    location_preference: Optional[str] = None
    total_budget_usd: Optional[int] = Field(default=None, ge=1)

    @property
    def missing_groups(self) -> list[str]:
        return [group.group_id for group in [*self.flight_groups, *self.hotel_groups] if not group.options]

    @property
    def is_complete(self) -> bool:
        return bool(self.flight_groups or self.hotel_groups) and not self.missing_groups


class BudgetAssessment(DecisionModel):
    minimum_flight_cost_usd: int
    minimum_hotel_cost_usd: int
    minimum_total_cost_usd: int
    is_complete: bool
    missing_groups: list[str]
    total_budget_usd: Optional[int]
    within_budget: Optional[bool]
    shortfall_usd: int


class RecommendedFlight(DecisionModel):
    group_id: str
    label: str
    option: FlightOption
    score: float = Field(ge=0, le=100)
    reasons: list[str]


class RecommendedHotel(DecisionModel):
    group_id: str
    label: str
    nights: int
    option: HotelOption
    score: float = Field(ge=0, le=100)
    reasons: list[str]


class Recommendation(DecisionModel):
    strategy: DecisionStrategy
    flights: list[RecommendedFlight]
    hotels: list[RecommendedHotel]
    estimated_total_usd: int
    is_complete: bool
    missing_groups: list[str]
    within_budget: Optional[bool]
    budget_adjusted: bool = False
    warnings: list[str] = Field(default_factory=list)


# Reuse the search agents' UUID, timestamp, and protocol validation while
# constraining identities to the two new specialists.
class BudgetRequestMetadata(A2ARequestMetadata):
    receiver_agent_id: Literal["budget-agent"] = "budget-agent"


class BudgetResponseMetadata(A2AResponseMetadata):
    agent_id: Literal["budget-agent"] = "budget-agent"


class RecommendationRequestMetadata(A2ARequestMetadata):
    receiver_agent_id: Literal["recommendation-agent"] = "recommendation-agent"


class RecommendationResponseMetadata(A2AResponseMetadata):
    agent_id: Literal["recommendation-agent"] = "recommendation-agent"


class DecisionTaskRequest(DecisionModel):
    task_id: str = Field(default_factory=new_task_id)
    session_id: str
    parameters: DecisionParameters

    @field_validator("task_id", "session_id")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        return str(UUID(value))


class BudgetTaskRequest(DecisionTaskRequest):
    task_type: Literal["budget_assessment"] = "budget_assessment"
    metadata: BudgetRequestMetadata = Field(default_factory=BudgetRequestMetadata)


class RecommendationTaskRequest(DecisionTaskRequest):
    task_type: Literal["option_recommendation"] = "option_recommendation"
    metadata: RecommendationRequestMetadata = Field(default_factory=RecommendationRequestMetadata)


Result = TypeVar("Result")


class DecisionTaskResponse(DecisionModel, Generic[Result]):
    task_id: str
    status: Literal["success", "partial"]
    results: list[Result] = Field(min_length=1)
    clarification_needed: Optional[str] = None
    error: None = None

    @field_validator("task_id")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        return str(UUID(value))

    @model_validator(mode="after")
    def validate_status_payload(self):
        if (self.status == "partial") != bool(self.clarification_needed):
            raise ValueError("Partial decision responses require clarification; success responses cannot include it.")
        self.metadata.result_count = len(self.results)
        return self


class BudgetTaskResponse(DecisionTaskResponse[BudgetAssessment]):
    metadata: BudgetResponseMetadata = Field(default_factory=BudgetResponseMetadata)


class RecommendationTaskResponse(DecisionTaskResponse[Recommendation]):
    metadata: RecommendationResponseMetadata = Field(default_factory=RecommendationResponseMetadata)
