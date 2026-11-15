"""Behavioral tests for the two offline decision graphs."""

from uuid import uuid4

import pytest

from agents.flight_agent.schemas import FlightOption
from agents.hotel_agent.schemas import HotelOption


def decision_parameters(**overrides):
    from agents.decision_schemas import DecisionParameters

    slow = FlightOption(
        trip_leg="outbound", airline="Mock Air", flight_number="MA100",
        origin="SIN", destination="TYO", departure_date="2027-07-25",
        departure_time="08:00", arrival_time="18:00", duration="10h 00m",
        stops=1, price_usd=100,
    )
    fast = slow.model_copy(update={"flight_number": "MA200", "price_usd": 160, "duration": "6h 00m", "stops": 0})
    inbound = slow.model_copy(update={
        "trip_leg": "inbound", "flight_number": "MA101", "origin": "TYO",
        "destination": "SIN", "departure_date": slow.departure_date,
        "price_usd": 110,
    })
    cheap_hotel = HotelOption(
        hotel_name="Budget Stay", destination="TYO", city_name="Tokyo",
        star_rating=3, area="Asakusa", price_per_night_usd=50,
        distance_from_landmark="0.5 km from Senso-ji", refundable=False,
    )
    premium_hotel = cheap_hotel.model_copy(update={
        "hotel_name": "Comfort Stay", "star_rating": 5, "area": "Shinjuku",
        "price_per_night_usd": 100, "refundable": True,
        "distance_from_landmark": "0.3 km from Shinjuku Station",
    })
    return DecisionParameters.model_validate({
        "passengers": 2,
        "flight_groups": [
            {"group_id": "outbound", "label": "SIN to TYO", "options": [slow, fast]},
            {"group_id": "return", "label": "TYO to SIN", "options": [inbound]},
        ],
        "hotel_groups": [{"group_id": "stay-1", "label": "Tokyo", "nights": 3, "options": [cheap_hotel, premium_hotel]}],
        **overrides,
    })


def budget_response(parameters):
    from agents.budget_agent.agent import BudgetDecisionAgent
    from agents.decision_schemas import BudgetTaskRequest

    return BudgetDecisionAgent().invoke(BudgetTaskRequest(session_id=str(uuid4()), parameters=parameters))


def recommendation_response(parameters):
    from agents.decision_schemas import RecommendationTaskRequest
    from agents.recommendation_agent.agent import RecommendationAgent

    return RecommendationAgent().invoke(RecommendationTaskRequest(session_id=str(uuid4()), parameters=parameters))


def test_budget_counts_both_flight_legs_all_passengers_and_hotel_nights():
    result = budget_response(decision_parameters(total_budget_usd=600)).results[0]
    assert result.minimum_flight_cost_usd == 420
    assert result.minimum_hotel_cost_usd == 150
    assert result.minimum_total_cost_usd == 570
    assert result.is_complete
    assert result.within_budget is True
    assert result.shortfall_usd == 0


def test_budget_adds_each_city_stay_without_multiplying_rooms_by_guests():
    parameters = decision_parameters()
    second_stay = parameters.hotel_groups[0].model_copy(update={"group_id": "stay-2", "label": "Paris", "nights": 2})
    parameters.hotel_groups.append(second_stay)
    result = budget_response(parameters).results[0]
    assert result.minimum_total_cost_usd == 670
    assert result.minimum_hotel_cost_usd == 250


def test_budget_reports_the_exact_shortfall():
    result = budget_response(decision_parameters(total_budget_usd=500)).results[0]
    assert result.within_budget is False
    assert result.shortfall_usd == 70


def test_missing_return_is_a_partial_subtotal_not_an_affordable_complete_trip():
    parameters = decision_parameters(total_budget_usd=600)
    parameters.flight_groups[1].options = []
    response = budget_response(parameters)
    assert response.status == "partial"
    assert response.clarification_needed
    result = response.results[0]
    assert result.minimum_total_cost_usd == 350
    assert result.missing_groups == ["return"]
    assert result.is_complete is False
    assert result.within_budget is None


@pytest.mark.parametrize("strategy,flight,hotel", [
    ("budget", "MA100", "Budget Stay"),
    ("comfort", "MA200", "Comfort Stay"),
])
def test_strategy_changes_recommended_options(strategy, flight, hotel):
    result = recommendation_response(decision_parameters(strategy=strategy)).results[0]
    assert result.flights[0].option.flight_number == flight
    assert result.hotels[0].option.hotel_name == hotel
    assert result.flights[0].reasons
    assert result.hotels[0].reasons
    assert result.strategy == strategy


def test_recommended_cost_uses_selected_options_instead_of_minimum_prices():
    result = recommendation_response(decision_parameters(strategy="comfort")).results[0]
    assert result.estimated_total_usd == 840
    assert result.is_complete


def test_total_budget_takes_priority_over_comfort_when_a_cheaper_plan_fits():
    result = recommendation_response(decision_parameters(strategy="comfort", total_budget_usd=600)).results[0]
    assert result.budget_adjusted
    assert result.estimated_total_usd == 570
    assert result.within_budget is True
    assert result.flights[0].option.flight_number == "MA100"
    assert result.hotels[0].option.hotel_name == "Budget Stay"
    assert result.warnings


def test_impossible_total_budget_is_explicit_in_recommendation():
    result = recommendation_response(decision_parameters(total_budget_usd=500)).results[0]
    assert result.estimated_total_usd == 570
    assert result.within_budget is False
    assert result.warnings


def test_missing_hotel_marks_recommendation_incomplete():
    parameters = decision_parameters()
    parameters.hotel_groups[0].options = []
    response = recommendation_response(parameters)
    assert response.status == "partial"
    assert response.results[0].missing_groups == ["stay-1"]
    assert response.results[0].is_complete is False
    assert not response.results[0].hotels


def test_balanced_strategy_honors_location_when_other_properties_match():
    parameters = decision_parameters(strategy="balanced", location_preference="near Shinjuku")
    first, second = parameters.hotel_groups[0].options
    parameters.hotel_groups[0].options[1] = second.model_copy(update={
        "price_per_night_usd": first.price_per_night_usd,
        "star_rating": first.star_rating, "refundable": first.refundable,
    })
    result = recommendation_response(parameters).results[0]
    assert result.hotels[0].option.hotel_name == "Comfort Stay"
    assert any("Shinjuku" in reason for reason in result.hotels[0].reasons)


def test_recommendation_keeps_the_callers_search_results_in_their_original_order():
    parameters = decision_parameters(strategy="comfort")
    before = parameters.model_dump()
    recommendation_response(parameters)
    assert parameters.model_dump() == before


@pytest.mark.parametrize("kind", ["budget", "recommendation"])
def test_decision_a2a_json_round_trip_correlates_task_and_trace(kind):
    from agents.budget_agent.agent import BudgetDecisionAgent
    from agents.decision_schemas import BudgetTaskRequest, RecommendationTaskRequest
    from agents.recommendation_agent.agent import RecommendationAgent

    request_type, agent = (BudgetTaskRequest, BudgetDecisionAgent()) if kind == "budget" else (RecommendationTaskRequest, RecommendationAgent())
    request = request_type(session_id=str(uuid4()), parameters=decision_parameters())
    response = agent.invoke(request.model_dump(mode="json"))
    assert response.task_id == request.task_id
    assert response.metadata.trace_id == request.metadata.trace_id
    assert response.metadata.agent_id == request.metadata.receiver_agent_id
    assert response.metadata.result_count == 1
    assert response.model_dump(mode="json")["status"] == "success"
