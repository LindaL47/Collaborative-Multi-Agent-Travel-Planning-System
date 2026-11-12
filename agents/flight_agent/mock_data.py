"""Stable mock flight data and deterministic search helpers."""

from __future__ import annotations

import math
from datetime import date
from typing import Dict, Iterable, List, Tuple

from agents.flight_agent.schemas import CabinClass, FlightOption


MOCK_FLIGHTS: List[FlightOption] = [
    FlightOption(trip_leg="outbound", airline="Singapore Airlines", flight_number="SQ632", origin="SIN", destination="TYO", departure_date=date(2025, 6, 15), departure_time="08:05", arrival_time="16:10", duration="7h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=540, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Japan Airlines", flight_number="JL712", origin="SIN", destination="TYO", departure_date=date(2025, 6, 15), departure_time="22:25", arrival_time="06:30+1", duration="7h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=515, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Singapore Airlines", flight_number="SQ633", origin="TYO", destination="SIN", departure_date=date(2025, 6, 20), departure_time="17:00", arrival_time="23:15", duration="7h 15m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=558, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Japan Airlines", flight_number="JL711", origin="TYO", destination="SIN", departure_date=date(2025, 6, 20), departure_time="10:20", arrival_time="16:35", duration="7h 15m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=530, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Singapore Airlines", flight_number="SQ632", origin="SIN", destination="TYO", departure_date=date(2025, 6, 15), departure_time="08:05", arrival_time="16:10", duration="7h 05m", stops=0, cabin_class=CabinClass.BUSINESS, price_usd=2140, baggage_note="40kg baggage and lounge access"),
    FlightOption(trip_leg="inbound", airline="Singapore Airlines", flight_number="SQ633", origin="TYO", destination="SIN", departure_date=date(2025, 6, 20), departure_time="17:00", arrival_time="23:15", duration="7h 15m", stops=0, cabin_class=CabinClass.BUSINESS, price_usd=2195, baggage_note="40kg baggage and lounge access"),
    # Extra future-dated Tokyo options make multi-turn demo prompts using 2026 behave naturally.
    FlightOption(trip_leg="outbound", airline="Singapore Airlines", flight_number="SQ632", origin="SIN", destination="TYO", departure_date=date(2026, 7, 25), departure_time="08:05", arrival_time="16:10", duration="7h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=565, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Japan Airlines", flight_number="JL712", origin="SIN", destination="TYO", departure_date=date(2026, 7, 25), departure_time="22:25", arrival_time="06:30+1", duration="7h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=548, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Singapore Airlines", flight_number="SQ632", origin="SIN", destination="TYO", departure_date=date(2026, 7, 26), departure_time="08:05", arrival_time="16:10", duration="7h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=570, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Japan Airlines", flight_number="JL712", origin="SIN", destination="TYO", departure_date=date(2026, 7, 26), departure_time="22:25", arrival_time="06:30+1", duration="7h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=552, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Singapore Airlines", flight_number="SQ633", origin="TYO", destination="SIN", departure_date=date(2026, 7, 31), departure_time="17:00", arrival_time="23:15", duration="7h 15m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=585, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Japan Airlines", flight_number="JL711", origin="TYO", destination="SIN", departure_date=date(2026, 7, 31), departure_time="10:20", arrival_time="16:35", duration="7h 15m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=560, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Emirates", flight_number="EK355", origin="SIN", destination="DXB", departure_date=date(2025, 7, 10), departure_time="21:00", arrival_time="00:35+1", duration="7h 35m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=440, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Emirates", flight_number="EK354", origin="DXB", destination="SIN", departure_date=date(2025, 7, 18), departure_time="03:05", arrival_time="15:00", duration="7h 55m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=455, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="British Airways", flight_number="BA012", origin="SIN", destination="LON", departure_date=date(2025, 8, 5), departure_time="23:20", arrival_time="05:55+1", duration="13h 35m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=790, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="British Airways", flight_number="BA011", origin="LON", destination="SIN", departure_date=date(2025, 8, 12), departure_time="19:35", arrival_time="15:45+1", duration="13h 10m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=810, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Air France", flight_number="AF257", origin="SIN", destination="PAR", departure_date=date(2025, 7, 10), departure_time="22:35", arrival_time="06:10+1", duration="13h 35m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=760, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Air France", flight_number="AF256", origin="PAR", destination="SIN", departure_date=date(2025, 7, 18), departure_time="21:05", arrival_time="16:55+1", duration="12h 50m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=785, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Qantas", flight_number="QF082", origin="SIN", destination="SYD", departure_date=date(2025, 9, 3), departure_time="20:30", arrival_time="06:10+1", duration="7h 40m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=480, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Qantas", flight_number="QF081", origin="SYD", destination="SIN", departure_date=date(2025, 9, 10), departure_time="10:25", arrival_time="16:50", duration="8h 25m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=498, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Thai Airways", flight_number="TG404", origin="SIN", destination="BKK", departure_date=date(2025, 6, 21), departure_time="12:25", arrival_time="13:45", duration="2h 20m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=185, baggage_note="20kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Thai Airways", flight_number="TG403", origin="BKK", destination="SIN", departure_date=date(2025, 6, 25), departure_time="08:00", arrival_time="11:20", duration="2h 20m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=178, baggage_note="20kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Cathay Pacific", flight_number="CX714", origin="SIN", destination="HKG", departure_date=date(2025, 10, 1), departure_time="01:25", arrival_time="05:20", duration="3h 55m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=295, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Cathay Pacific", flight_number="CX715", origin="HKG", destination="SIN", departure_date=date(2025, 10, 5), departure_time="20:25", arrival_time="00:15+1", duration="3h 50m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=305, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Korean Air", flight_number="KE646", origin="SIN", destination="SEL", departure_date=date(2025, 11, 11), departure_time="01:10", arrival_time="08:35", duration="6h 25m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=470, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Korean Air", flight_number="KE645", origin="SEL", destination="SIN", departure_date=date(2025, 11, 17), departure_time="18:35", arrival_time="00:10+1", duration="6h 35m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=489, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Malaysia Airlines", flight_number="MH604", origin="SIN", destination="KUL", departure_date=date(2025, 6, 10), departure_time="10:30", arrival_time="11:35", duration="1h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=95, baggage_note="20kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Malaysia Airlines", flight_number="MH603", origin="KUL", destination="SIN", departure_date=date(2025, 6, 14), departure_time="12:10", arrival_time="13:15", duration="1h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=98, baggage_note="20kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="IndiGo", flight_number="6E1012", origin="SIN", destination="BLR", departure_date=date(2025, 12, 2), departure_time="19:40", arrival_time="21:50", duration="4h 40m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=245, baggage_note="15kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="IndiGo", flight_number="6E1009", origin="BLR", destination="SIN", departure_date=date(2025, 12, 8), departure_time="23:15", arrival_time="06:20+1", duration="4h 35m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=260, baggage_note="15kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Japan Airlines", flight_number="JL754", origin="BLR", destination="TYO", departure_date=date(2025, 1, 1), departure_time="02:35", arrival_time="17:20", duration="11h 15m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=640, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Air India", flight_number="AI306", origin="BLR", destination="TYO", departure_date=date(2025, 1, 1), departure_time="07:10", arrival_time="22:45", duration="12h 05m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=610, baggage_note="25kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Japan Airlines", flight_number="JL753", origin="TYO", destination="BLR", departure_date=date(2025, 1, 1), departure_time="10:40", arrival_time="23:55", duration="10h 45m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=635, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Air India", flight_number="AI307", origin="TYO", destination="BLR", departure_date=date(2025, 1, 1), departure_time="11:30", arrival_time="00:20+1", duration="10h 20m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=605, baggage_note="25kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Air India", flight_number="AI381", origin="SIN", destination="DEL", departure_date=date(2025, 12, 15), departure_time="08:20", arrival_time="11:45", duration="5h 55m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=330, baggage_note="25kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Air India", flight_number="AI382", origin="DEL", destination="SIN", departure_date=date(2025, 12, 22), departure_time="13:15", arrival_time="21:25", duration="5h 40m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=345, baggage_note="25kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Vistara", flight_number="UK108", origin="SIN", destination="BOM", departure_date=date(2025, 12, 20), departure_time="21:20", arrival_time="00:15+1", duration="5h 25m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=315, baggage_note="25kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Vistara", flight_number="UK107", origin="BOM", destination="SIN", departure_date=date(2025, 12, 27), departure_time="10:25", arrival_time="18:30", duration="5h 35m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=330, baggage_note="25kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Batik Air", flight_number="ID7130", origin="SIN", destination="DPS", departure_date=date(2025, 8, 18), departure_time="16:15", arrival_time="18:55", duration="2h 40m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=210, baggage_note="20kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Batik Air", flight_number="ID7131", origin="DPS", destination="SIN", departure_date=date(2025, 8, 23), departure_time="12:40", arrival_time="15:25", duration="2h 45m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=205, baggage_note="20kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="Lufthansa", flight_number="LH779", origin="SIN", destination="ZRH", departure_date=date(2025, 9, 12), departure_time="23:40", arrival_time="06:25+1", duration="12h 45m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=850, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Swiss", flight_number="LX176", origin="ZRH", destination="SIN", departure_date=date(2025, 9, 19), departure_time="22:40", arrival_time="17:05+1", duration="12h 25m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=870, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="ITA Airways", flight_number="AZ779", origin="SIN", destination="ROM", departure_date=date(2025, 10, 9), departure_time="23:45", arrival_time="08:15+1", duration="14h 30m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=720, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="ITA Airways", flight_number="AZ778", origin="ROM", destination="SIN", departure_date=date(2025, 10, 16), departure_time="20:20", arrival_time="17:40+1", duration="15h 20m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=735, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Qatar Airways", flight_number="QR947", origin="SIN", destination="BCN", departure_date=date(2025, 11, 6), departure_time="18:45", arrival_time="07:35+1", duration="19h 50m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=820, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="inbound", airline="Qatar Airways", flight_number="QR146", origin="BCN", destination="SIN", departure_date=date(2025, 11, 13), departure_time="16:25", arrival_time="15:10+1", duration="15h 45m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=835, baggage_note="30kg checked baggage included"),
    FlightOption(trip_leg="outbound", airline="United Airlines", flight_number="UA002", origin="SIN", destination="SFO", departure_date=date(2025, 9, 25), departure_time="08:45", arrival_time="09:50", duration="15h 05m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=980, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="United Airlines", flight_number="UA001", origin="SFO", destination="SIN", departure_date=date(2025, 10, 3), departure_time="22:40", arrival_time="06:15+2", duration="16h 35m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=995, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Air Canada", flight_number="AC020", origin="SIN", destination="YYZ", departure_date=date(2025, 10, 20), departure_time="09:10", arrival_time="18:35", duration="21h 25m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=1085, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Air Canada", flight_number="AC019", origin="YYZ", destination="SIN", departure_date=date(2025, 10, 28), departure_time="00:40", arrival_time="07:20+2", duration="22h 40m", stops=1, cabin_class=CabinClass.ECONOMY, price_usd=1110, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="American Airlines", flight_number="AA100", origin="NYC", destination="LON", departure_date=date(2025, 6, 15), departure_time="18:20", arrival_time="06:45+1", duration="7h 25m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=610, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="American Airlines", flight_number="AA101", origin="LON", destination="NYC", departure_date=date(2025, 6, 22), departure_time="10:10", arrival_time="13:20", duration="8h 10m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=645, baggage_note="1 checked bag included"),
    # Open-jaw / multi-city templates used when users return to a third city.
    FlightOption(trip_leg="inbound", airline="Air France", flight_number="AF275", origin="TYO", destination="PAR", departure_date=date(2025, 6, 20), departure_time="11:45", arrival_time="18:35", duration="14h 50m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=920, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="inbound", airline="Japan Airlines", flight_number="JL045", origin="TYO", destination="PAR", departure_date=date(2025, 6, 20), departure_time="10:20", arrival_time="17:35", duration="15h 15m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=945, baggage_note="1 checked bag included"),
    FlightOption(trip_leg="outbound", airline="Air France", flight_number="AF274", origin="PAR", destination="TYO", departure_date=date(2025, 7, 1), departure_time="22:00", arrival_time="18:30+1", duration="13h 30m", stops=0, cabin_class=CabinClass.ECONOMY, price_usd=910, baggage_note="1 checked bag included"),

]

CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "SIN": (1.3521, 103.8198),
    "TYO": (35.6762, 139.6503),
    "PAR": (48.8566, 2.3522),
    "DXB": (25.2048, 55.2708),
    "LON": (51.5074, -0.1278),
    "SYD": (-33.8688, 151.2093),
    "BKK": (13.7563, 100.5018),
    "HKG": (22.3193, 114.1694),
    "SEL": (37.5665, 126.9780),
    "KUL": (3.1390, 101.6869),
    "BLR": (12.9716, 77.5946),
    "DEL": (28.6139, 77.2090),
    "BOM": (19.0760, 72.8777),
    "DPS": (-8.3405, 115.0920),
    "ZRH": (47.3769, 8.5417),
    "ROM": (41.9028, 12.4964),
    "BCN": (41.3874, 2.1686),
    "SFO": (37.7749, -122.4194),
    "YYZ": (43.6532, -79.3832),
    "NYC": (40.7128, -74.0060),
    "MEX": (19.4326, -99.1332),
}

CITY_REGIONS: Dict[str, str] = {
    "SIN": "southeast_asia",
    "BKK": "southeast_asia",
    "KUL": "southeast_asia",
    "DPS": "southeast_asia",
    "TYO": "east_asia",
    "HKG": "east_asia",
    "SEL": "east_asia",
    "BLR": "india",
    "DEL": "india",
    "BOM": "india",
    "DXB": "middle_east",
    "PAR": "europe",
    "LON": "europe",
    "ZRH": "europe",
    "ROM": "europe",
    "BCN": "europe",
    "SFO": "north_america",
    "YYZ": "north_america",
    "NYC": "north_america",
    "MEX": "north_america",
    "SYD": "oceania",
}

REGION_AIRLINES: Dict[str, List[tuple[str, str]]] = {
    "southeast_asia": [("Singapore Airlines", "SQ"), ("Scoot", "TR"), ("Malaysia Airlines", "MH")],
    "east_asia": [("Japan Airlines", "JL"), ("ANA", "NH"), ("Korean Air", "KE")],
    "india": [("Air India", "AI"), ("IndiGo", "6E"), ("Vistara", "UK")],
    "middle_east": [("Emirates", "EK"), ("Qatar Airways", "QR"), ("Etihad Airways", "EY")],
    "europe": [("Air France", "AF"), ("British Airways", "BA"), ("Lufthansa", "LH")],
    "north_america": [("United Airlines", "UA"), ("Air Canada", "AC"), ("American Airlines", "AA")],
    "oceania": [("Qantas", "QF"), ("Singapore Airlines", "SQ"), ("Jetstar", "JQ")],
}

SUPPORTED_DYNAMIC_CODES = set(CITY_COORDINATES)
UNSUPPORTED_DYNAMIC_CODES = {"KEF"}


def _matching_options(origin: str, destination: str, travel_date: date, cabin_class: str) -> List[FlightOption]:
    origin = origin.upper()
    destination = destination.upper()
    cabin_value = str(cabin_class)
    return [
        option
        for option in MOCK_FLIGHTS
        if option.origin == origin
        and option.destination == destination
        and option.departure_date == travel_date
        and option.cabin_class == cabin_value
    ]


def _route_templates(origin: str, destination: str, cabin_class: str) -> List[FlightOption]:
    """Return reusable templates for a supported route.

    Exact dates are intentionally sparse in mock assignments. For a better
    conversational demo, supported city pairs can produce deterministic synthetic
    options on user-provided dates. Unsupported routes, like SIN → KEF, still
    return no data for the required no-availability test.
    """
    origin = origin.upper()
    destination = destination.upper()
    cabin_value = str(cabin_class)
    exact = [
        option
        for option in MOCK_FLIGHTS
        if option.origin == origin and option.destination == destination and option.cabin_class == cabin_value
    ]
    if exact:
        return exact[:2]

    economy = [
        option
        for option in MOCK_FLIGHTS
        if option.origin == origin and option.destination == destination and option.cabin_class == CabinClass.ECONOMY
    ]
    if economy and cabin_value != CabinClass.ECONOMY.value:
        return [
            option.model_copy(update={
                "cabin_class": cabin_value,
                "price_usd": int(option.price_usd * (3.6 if cabin_value == CabinClass.BUSINESS.value else 1.8)),
                "baggage_note": "Enhanced baggage and priority services",
            })
            for option in economy[:2]
        ]
    if economy:
        return economy[:2]

    if _supports_dynamic_route(origin, destination):
        return _dynamic_route_templates(origin, destination, cabin_value)

    return []


def _supports_dynamic_route(origin: str, destination: str) -> bool:
    return (
        origin in SUPPORTED_DYNAMIC_CODES
        and destination in SUPPORTED_DYNAMIC_CODES
        and origin != destination
        and origin not in UNSUPPORTED_DYNAMIC_CODES
        and destination not in UNSUPPORTED_DYNAMIC_CODES
    )


def _distance_km(origin: str, destination: str) -> float:
    lat1, lon1 = CITY_COORDINATES[origin]
    lat2, lon2 = CITY_COORDINATES[destination]
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _duration_minutes(distance_km: float, stops: int) -> int:
    cruise_minutes = int((distance_km / 830) * 60)
    return max(65, cruise_minutes + 55 + (stops * 85))


def _format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m"


def _time_text(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}"


def _arrival_text(departure_minutes: int, duration_minutes: int) -> str:
    total = departure_minutes + duration_minutes
    suffix = ""
    if total >= 48 * 60:
        suffix = "+2"
    elif total >= 24 * 60:
        suffix = "+1"
    return _time_text(total) + suffix


def _airline_choices(origin: str, destination: str) -> List[tuple[str, str]]:
    choices: List[tuple[str, str]] = []
    for code in [origin, destination]:
        region = CITY_REGIONS.get(code)
        if region:
            choices.extend(REGION_AIRLINES.get(region, []))
    unique: List[tuple[str, str]] = []
    for airline in choices:
        if airline not in unique:
            unique.append(airline)
    return (unique or [("Global Airways", "GA"), ("WorldConnect Air", "WA")])[:2]


def _cabin_multiplier(cabin_class: str) -> float:
    return {
        CabinClass.ECONOMY.value: 1.0,
        CabinClass.PREMIUM_ECONOMY.value: 1.55,
        CabinClass.BUSINESS.value: 3.4,
        CabinClass.FIRST.value: 5.8,
    }.get(str(cabin_class), 1.0)


def _baggage_note(cabin_class: str, stops: int) -> str:
    if cabin_class == CabinClass.BUSINESS.value:
        return "40kg baggage and lounge access"
    if cabin_class == CabinClass.FIRST.value:
        return "50kg baggage, lounge access, and priority services"
    if cabin_class == CabinClass.PREMIUM_ECONOMY.value:
        return "2 checked bags included"
    return "1 checked bag included" if stops else "30kg checked baggage included"


def _dynamic_route_templates(origin: str, destination: str, cabin_class: str) -> List[FlightOption]:
    distance = _distance_km(origin, destination)
    stops = 0 if distance < 7500 else 1
    duration = _duration_minutes(distance, stops)
    seed = sum(ord(ch) for ch in f"{origin}{destination}")
    base_price = int((95 + distance * 0.075 + (35 if stops else 0)) * _cabin_multiplier(cabin_class))
    departures = [7 * 60 + (seed % 95), 18 * 60 + ((seed * 3) % 140)]
    templates: List[FlightOption] = []
    for idx, (airline, prefix) in enumerate(_airline_choices(origin, destination)):
        depart = departures[idx]
        templates.append(
            FlightOption(
                trip_leg="outbound",
                airline=airline,
                flight_number=f"{prefix}{100 + ((seed + idx * 137) % 850)}",
                origin=origin,
                destination=destination,
                departure_date=date(2025, 1, 1),
                departure_time=_time_text(depart),
                arrival_time=_arrival_text(depart, duration + idx * 35),
                duration=_format_duration(duration + idx * 35),
                stops=stops if idx == 0 else min(stops + 1, 2),
                cabin_class=CabinClass(cabin_class),
                price_usd=base_price + (idx * 48),
                baggage_note=_baggage_note(cabin_class, stops if idx == 0 else min(stops + 1, 2)),
            )
        )
    return templates


def _synthetic_options(origin: str, destination: str, travel_date: date, cabin_class: str, trip_leg: str) -> List[FlightOption]:
    templates = _route_templates(origin, destination, cabin_class)
    if not templates:
        return []
    day_adjustment = (travel_date.toordinal() % 9) * 4
    options: List[FlightOption] = []
    for idx, template in enumerate(templates[:2]):
        options.append(
            template.model_copy(
                update={
                    "trip_leg": trip_leg,
                    "departure_date": travel_date,
                    "price_usd": template.price_usd + day_adjustment + (idx * 12),
                }
            )
        )
    return options


def search_mock_flights(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: date | None,
    cabin_class: str,
    return_destination: str | None = None,
) -> List[FlightOption]:
    """Return stable mock flight options for a one-way or round-trip request."""
    outbound = _matching_options(origin, destination, departure_date, cabin_class)
    if not outbound:
        outbound = _synthetic_options(origin, destination, departure_date, cabin_class, "outbound")
    else:
        outbound = [option.model_copy(update={"trip_leg": "outbound"}) for option in outbound]

    if not return_date:
        return outbound

    inbound_destination = (return_destination or origin).upper()
    inbound = _matching_options(destination, inbound_destination, return_date, cabin_class)
    if not inbound:
        inbound = _synthetic_options(destination, inbound_destination, return_date, cabin_class, "inbound")
    else:
        inbound = [option.model_copy(update={"trip_leg": "inbound"}) for option in inbound]
    return outbound + inbound


def available_route_suggestions(origin: str, limit: int = 5) -> List[str]:
    """Return known destinations from the supplied origin for friendly fallbacks."""
    origin = origin.upper()
    destinations = []
    for option in MOCK_FLIGHTS:
        if option.origin == origin and option.destination not in destinations:
            destinations.append(option.destination)
    return destinations[:limit]


def count_distinct_city_pairs(flights: Iterable[FlightOption] = MOCK_FLIGHTS) -> int:
    """Return distinct route count for tests/documentation."""
    return len({(flight.origin, flight.destination) for flight in flights})
