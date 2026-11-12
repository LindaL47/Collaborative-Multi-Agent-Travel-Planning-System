"""Stable mock hotel data and deterministic search helpers."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from agents.hotel_agent.schemas import HotelOption, RoomType, normalize_city_code


MOCK_HOTELS: List[HotelOption] = [
    HotelOption(hotel_name="Shinjuku Garden Hotel", destination="TYO", city_name="Tokyo", star_rating=4.5, area="Shinjuku", price_per_night_usd=210, amenities=["Breakfast", "Metro access", "Free Wi-Fi"], distance_from_landmark="0.4 km from Shinjuku Station", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Tokyo Bay View Suites", destination="TYO", city_name="Tokyo", star_rating=5.0, area="Ginza", price_per_night_usd=360, amenities=["Spa", "Rooftop bar", "Airport transfer"], distance_from_landmark="1.2 km from Ginza Crossing", room_type=RoomType.SUITE),
    HotelOption(hotel_name="Asakusa Comfort Inn", destination="TYO", city_name="Tokyo", star_rating=3.5, area="Asakusa", price_per_night_usd=135, amenities=["Free Wi-Fi", "Laundry", "Family rooms"], distance_from_landmark="0.6 km from Senso-ji", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Marina Bay Business Hotel", destination="SIN", city_name="Singapore", star_rating=4.5, area="Marina Bay", price_per_night_usd=245, amenities=["Pool", "Breakfast", "MRT access"], distance_from_landmark="0.8 km from Marina Bay Sands", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Orchard Urban Stay", destination="SIN", city_name="Singapore", star_rating=4.0, area="Orchard", price_per_night_usd=190, amenities=["Gym", "Free Wi-Fi", "Shopping district"], distance_from_landmark="0.3 km from Orchard Road", room_type=RoomType.DELUXE),
    HotelOption(hotel_name="Downtown Dubai Terrace", destination="DXB", city_name="Dubai", star_rating=5.0, area="Downtown", price_per_night_usd=310, amenities=["Burj view", "Pool", "Valet parking"], distance_from_landmark="0.7 km from Burj Khalifa", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Deira Creek Hotel", destination="DXB", city_name="Dubai", star_rating=4.0, area="Deira", price_per_night_usd=130, amenities=["Breakfast", "Airport shuttle", "Free Wi-Fi"], distance_from_landmark="1.0 km from Dubai Creek", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Westminster Park Hotel", destination="LON", city_name="London", star_rating=4.5, area="Westminster", price_per_night_usd=280, amenities=["Breakfast", "River view", "Tube access"], distance_from_landmark="0.5 km from Big Ben", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Shoreditch Creative Stay", destination="LON", city_name="London", star_rating=4.0, area="Shoreditch", price_per_night_usd=220, amenities=["Co-working lounge", "Free Wi-Fi", "Cafe"], distance_from_landmark="0.4 km from Shoreditch High Street", room_type=RoomType.DELUXE),
    HotelOption(hotel_name="Saint-Germain Boutique", destination="PAR", city_name="Paris", star_rating=4.5, area="Saint-Germain", price_per_night_usd=260, amenities=["Breakfast", "Boutique rooms", "Metro access"], distance_from_landmark="1.0 km from Louvre Museum", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Eiffel Garden Residence", destination="PAR", city_name="Paris", star_rating=5.0, area="7th Arrondissement", price_per_night_usd=420, amenities=["Eiffel view", "Spa", "Fine dining"], distance_from_landmark="0.6 km from Eiffel Tower", room_type=RoomType.SUITE),
    HotelOption(hotel_name="Circular Quay Harbour Hotel", destination="SYD", city_name="Sydney", star_rating=4.5, area="Circular Quay", price_per_night_usd=240, amenities=["Harbour view", "Breakfast", "Gym"], distance_from_landmark="0.5 km from Sydney Opera House", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Sukhumvit City Lodge", destination="BKK", city_name="Bangkok", star_rating=4.0, area="Sukhumvit", price_per_night_usd=105, amenities=["BTS access", "Pool", "Free Wi-Fi"], distance_from_landmark="0.3 km from Asok BTS", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Kowloon Skyline Hotel", destination="HKG", city_name="Hong Kong", star_rating=4.5, area="Tsim Sha Tsui", price_per_night_usd=210, amenities=["Harbour view", "MTR access", "Breakfast"], distance_from_landmark="0.6 km from Victoria Harbour", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Myeongdong Central Stay", destination="SEL", city_name="Seoul", star_rating=4.0, area="Myeongdong", price_per_night_usd=155, amenities=["Metro access", "Laundry", "Free Wi-Fi"], distance_from_landmark="0.2 km from Myeongdong Station", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="KLCC Executive Hotel", destination="KUL", city_name="Kuala Lumpur", star_rating=4.5, area="KLCC", price_per_night_usd=145, amenities=["Pool", "Breakfast", "City view"], distance_from_landmark="0.4 km from Petronas Towers", room_type=RoomType.DELUXE),
    HotelOption(hotel_name="Bengaluru Tech Park Inn", destination="BLR", city_name="Bengaluru", star_rating=4.0, area="Whitefield", price_per_night_usd=95, amenities=["Breakfast", "Business centre", "Airport transfer"], distance_from_landmark="1.5 km from ITPL", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="MG Road Executive Hotel", destination="BLR", city_name="Bengaluru", star_rating=4.5, area="MG Road", price_per_night_usd=130, amenities=["Metro access", "Breakfast", "Business lounge"], distance_from_landmark="0.4 km from MG Road Metro", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Indiranagar Urban Suites", destination="BLR", city_name="Bengaluru", star_rating=4.5, area="Indiranagar", price_per_night_usd=155, amenities=["Suite rooms", "Cafe", "Airport transfer"], distance_from_landmark="0.6 km from 100 Feet Road", room_type=RoomType.SUITE),
    HotelOption(hotel_name="Connaught Place Heritage", destination="DEL", city_name="Delhi", star_rating=4.0, area="Connaught Place", price_per_night_usd=125, amenities=["Metro access", "Breakfast", "Free Wi-Fi"], distance_from_landmark="0.5 km from Rajiv Chowk", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Bandra Sea Link Hotel", destination="BOM", city_name="Mumbai", star_rating=4.5, area="Bandra", price_per_night_usd=170, amenities=["Sea view", "Breakfast", "Gym"], distance_from_landmark="0.9 km from Bandra-Worli Sea Link", room_type=RoomType.DELUXE),
    HotelOption(hotel_name="Seminyak Beach Retreat", destination="DPS", city_name="Bali", star_rating=4.5, area="Seminyak", price_per_night_usd=185, amenities=["Beach access", "Pool", "Spa"], distance_from_landmark="0.3 km from Seminyak Beach", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Zurich Old Town Hotel", destination="ZRH", city_name="Zurich", star_rating=4.0, area="Old Town", price_per_night_usd=235, amenities=["Tram access", "Breakfast", "Free Wi-Fi"], distance_from_landmark="0.5 km from Bahnhofstrasse", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Colosseum View Rooms", destination="ROM", city_name="Rome", star_rating=4.0, area="Monti", price_per_night_usd=180, amenities=["Breakfast", "Historic district", "Free Wi-Fi"], distance_from_landmark="0.7 km from Colosseum", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Barcelona Gothic Quarter Stay", destination="BCN", city_name="Barcelona", star_rating=4.0, area="Gothic Quarter", price_per_night_usd=205, amenities=["Rooftop terrace", "Metro access", "Breakfast"], distance_from_landmark="0.4 km from Barcelona Cathedral", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Union Square City Hotel", destination="SFO", city_name="San Francisco", star_rating=4.0, area="Union Square", price_per_night_usd=260, amenities=["Cable car access", "Gym", "Free Wi-Fi"], distance_from_landmark="0.2 km from Union Square", room_type=RoomType.STANDARD),
    HotelOption(hotel_name="Toronto Harbourfront Suites", destination="YYZ", city_name="Toronto", star_rating=4.5, area="Harbourfront", price_per_night_usd=230, amenities=["Lake view", "Pool", "Breakfast"], distance_from_landmark="0.8 km from CN Tower", room_type=RoomType.SUITE),
    HotelOption(hotel_name="Midtown Manhattan Hotel", destination="NYC", city_name="New York", star_rating=4.0, area="Midtown", price_per_night_usd=310, amenities=["Subway access", "Gym", "Free Wi-Fi"], distance_from_landmark="0.6 km from Times Square", room_type=RoomType.STANDARD),
]


CITY_LABELS: Dict[str, str] = {
    "SIN": "Singapore",
    "TYO": "Tokyo",
    "PAR": "Paris",
    "DXB": "Dubai",
    "LON": "London",
    "SYD": "Sydney",
    "BKK": "Bangkok",
    "HKG": "Hong Kong",
    "SEL": "Seoul",
    "KUL": "Kuala Lumpur",
    "BLR": "Bengaluru",
    "DEL": "Delhi",
    "BOM": "Mumbai",
    "DPS": "Bali",
    "ZRH": "Zurich",
    "ROM": "Rome",
    "BCN": "Barcelona",
    "SFO": "San Francisco",
    "YYZ": "Toronto",
    "NYC": "New York",
    "MEX": "Mexico City",
}

CITY_DEFAULT_AREAS: Dict[str, List[Tuple[str, str]]] = {
    "SIN": [("Marina Bay", "Marina Bay Sands"), ("Orchard", "Orchard Road"), ("Chinatown", "Chinatown MRT")],
    "TYO": [("Shinjuku", "Shinjuku Station"), ("Ginza", "Ginza Crossing"), ("Asakusa", "Senso-ji")],
    "PAR": [("Saint-Germain", "Louvre Museum"), ("7th Arrondissement", "Eiffel Tower"), ("Le Marais", "Place des Vosges")],
    "DXB": [("Downtown", "Burj Khalifa"), ("Deira", "Dubai Creek"), ("Marina", "Dubai Marina")],
    "LON": [("Westminster", "Big Ben"), ("Shoreditch", "Shoreditch High Street"), ("Paddington", "Paddington Station")],
    "SYD": [("Circular Quay", "Sydney Opera House"), ("Darling Harbour", "Darling Harbour"), ("Surry Hills", "Central Station")],
    "BKK": [("Sukhumvit", "Asok BTS"), ("Siam", "Siam Paragon"), ("Silom", "Lumphini Park")],
    "HKG": [("Tsim Sha Tsui", "Victoria Harbour"), ("Central", "IFC Mall"), ("Causeway Bay", "Times Square")],
    "SEL": [("Myeongdong", "Myeongdong Station"), ("Hongdae", "Hongik University Street"), ("Gangnam", "Gangnam Station")],
    "KUL": [("KLCC", "Petronas Towers"), ("Bukit Bintang", "Pavilion Kuala Lumpur"), ("Sentral", "KL Sentral")],
    "BLR": [("MG Road", "MG Road Metro"), ("Indiranagar", "100 Feet Road"), ("Whitefield", "ITPL")],
    "DEL": [("Connaught Place", "Rajiv Chowk"), ("Aerocity", "Delhi Airport"), ("Saket", "Select Citywalk")],
    "BOM": [("Bandra", "Bandra-Worli Sea Link"), ("Colaba", "Gateway of India"), ("Powai", "Powai Lake")],
    "DPS": [("Seminyak", "Seminyak Beach"), ("Ubud", "Ubud Palace"), ("Nusa Dua", "Nusa Dua Beach")],
    "ZRH": [("Old Town", "Bahnhofstrasse"), ("Enge", "Lake Zurich"), ("Oerlikon", "Zurich Messe")],
    "ROM": [("Monti", "Colosseum"), ("Trastevere", "Piazza Santa Maria"), ("Prati", "Vatican Museums")],
    "BCN": [("Gothic Quarter", "Barcelona Cathedral"), ("Eixample", "Passeig de Gracia"), ("El Born", "Picasso Museum")],
    "SFO": [("Union Square", "Union Square"), ("SoMa", "Moscone Center"), ("Fisherman's Wharf", "Pier 39")],
    "YYZ": [("Harbourfront", "CN Tower"), ("Downtown", "Union Station"), ("Yorkville", "Royal Ontario Museum")],
    "NYC": [("Midtown", "Times Square"), ("SoHo", "Broadway-Lafayette"), ("Financial District", "Wall Street")],
    "MEX": [("Centro Historico", "Zocalo"), ("Roma Norte", "Roma Norte dining district"), ("Polanco", "Chapultepec Park")],
}

CITY_BASE_PRICES: Dict[str, int] = {
    "SIN": 210,
    "TYO": 195,
    "PAR": 240,
    "DXB": 220,
    "LON": 255,
    "SYD": 215,
    "BKK": 95,
    "HKG": 190,
    "SEL": 145,
    "KUL": 125,
    "BLR": 105,
    "DEL": 110,
    "BOM": 150,
    "DPS": 165,
    "ZRH": 225,
    "ROM": 170,
    "BCN": 190,
    "SFO": 255,
    "YYZ": 220,
    "NYC": 295,
    "MEX": 135,
}

SUPPORTED_DYNAMIC_CODES = set(CITY_LABELS)
UNSUPPORTED_DYNAMIC_CODES = {"KEF"}


def _normalize_room_type(room_type: str | RoomType | None) -> str:
    if room_type is None:
        return RoomType.STANDARD.value
    if isinstance(room_type, RoomType):
        return room_type.value
    cleaned = str(room_type).strip().lower().replace("-", " ").replace("_", " ")
    if cleaned.startswith("roomtype."):
        cleaned = cleaned.split(".", 1)[1]
    aliases = {
        "": RoomType.STANDARD.value,
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
    return aliases.get(cleaned, cleaned)


def _supports_dynamic_hotels(destination: str) -> bool:
    return destination in SUPPORTED_DYNAMIC_CODES and destination not in UNSUPPORTED_DYNAMIC_CODES


def _area_from_preference(location_preference: str | None) -> Tuple[str, str] | None:
    if not location_preference:
        return None
    cleaned = re.sub(r"\b(near|around|close to|by|next to|in|at)\b", " ", location_preference, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,")
    if not cleaned:
        cleaned = location_preference.strip(" .,")
    area = cleaned[:1].upper() + cleaned[1:]
    return area, area


def _amenities_for(room_type: str, index: int) -> List[str]:
    base = ["Free Wi-Fi", "Breakfast"]
    by_room = {
        RoomType.STANDARD.value: ["Transit access", "Flexible cancellation"],
        RoomType.DELUXE.value: ["Gym", "Late checkout"],
        RoomType.SUITE.value: ["Suite lounge", "Airport transfer"],
        RoomType.FAMILY.value: ["Family rooms", "Laundry"],
    }
    rotating = [["24-hour front desk"], ["City view"], ["Work desk"]]
    return base + by_room.get(room_type, ["Flexible cancellation"])[:1] + rotating[index % len(rotating)]


def _dynamic_hotel_options(destination: str, room_type: str, location_preference: str | None) -> List[HotelOption]:
    if not _supports_dynamic_hotels(destination):
        return []

    city_name = CITY_LABELS[destination]
    areas = CITY_DEFAULT_AREAS.get(destination, [("City Centre", "main station"), ("Downtown", "city centre"), ("Airport", "airport terminal")])
    preferred_area = _area_from_preference(location_preference)
    if preferred_area:
        areas = [preferred_area] + [area for area in areas if area[0].lower() != preferred_area[0].lower()]

    base_price = CITY_BASE_PRICES.get(destination, 150)
    room_multipliers = {
        RoomType.STANDARD.value: 1.0,
        RoomType.DELUXE.value: 1.25,
        RoomType.SUITE.value: 1.65,
        RoomType.FAMILY.value: 1.4,
    }
    star_by_room = {
        RoomType.STANDARD.value: 4.0,
        RoomType.DELUXE.value: 4.5,
        RoomType.SUITE.value: 5.0,
        RoomType.FAMILY.value: 4.0,
    }
    name_templates = [
        "{area} Central Hotel",
        "{city} Business Suites",
        "{area} Boutique Stay",
    ]
    selected_room = room_type if room_type in {item.value for item in RoomType} else RoomType.STANDARD.value
    options: List[HotelOption] = []
    for index in range(3):
        area, landmark = areas[index % len(areas)]
        price = int((base_price + index * 24) * room_multipliers[selected_room])
        options.append(
            HotelOption(
                hotel_name=name_templates[index].format(city=city_name, area=area),
                destination=destination,
                city_name=city_name,
                star_rating=star_by_room[selected_room],
                area=area,
                price_per_night_usd=price,
                amenities=_amenities_for(selected_room, index),
                distance_from_landmark=f"{0.4 + (index * 0.3):.1f} km from {landmark}",
                room_type=selected_room,
                refundable=index != 2,
            )
        )
    return options


def _location_score(hotel: HotelOption, location_preference: str | None) -> int:
    if not location_preference:
        return 0
    needle = location_preference.lower()
    return 0 if needle in hotel.area.lower() or needle in hotel.distance_from_landmark.lower() else 1


def search_mock_hotels(destination: str, room_type: str, location_preference: str | None = None) -> List[HotelOption]:
    """Return stable mock hotel options ranked by location preference and room type."""
    destination = normalize_city_code(destination)
    room_type = _normalize_room_type(room_type)
    matches = [hotel for hotel in MOCK_HOTELS if hotel.destination == destination]

    if not matches:
        matches = _dynamic_hotel_options(destination, room_type, location_preference)

    if room_type:
        exact_room_matches = [hotel for hotel in matches if hotel.room_type == room_type]
        if exact_room_matches:
            matches = exact_room_matches

    matches = sorted(
        matches,
        key=lambda hotel: (
            _location_score(hotel, location_preference),
            0 if hotel.room_type == room_type else 1,
            -hotel.star_rating,
            hotel.price_per_night_usd,
        ),
    )

    return matches[:3]


def available_hotel_destinations(limit: int = 8) -> List[str]:
    """Return known hotel destinations for friendly fallbacks."""
    destinations = []
    for hotel in MOCK_HOTELS:
        label = f"{hotel.city_name} ({hotel.destination})"
        if label not in destinations:
            destinations.append(label)
    for code, city_name in CITY_LABELS.items():
        label = f"{city_name} ({code})"
        if code not in UNSUPPORTED_DYNAMIC_CODES and label not in destinations:
            destinations.append(label)
    return destinations[:limit]
