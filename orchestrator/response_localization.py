"""Render verified planner state in the language selected by the UI.

Search values stay in their typed models. Only the user-facing explanation is
localized; this avoids sending dates and prices through a translation model.
"""

from __future__ import annotations

from typing import Any


SUPPORTED_LANGUAGES = {"en", "zh", "ja", "es"}

COPY = {
    "zh": {
        "intro": "为 {destination} 找到以下行程选项：", "flights": "航班选项", "hotels": "酒店选项",
        "flight": "{leg}：{airline} {number}，{origin} → {destination}，{date} {departure}–{arrival}，每人 ${price}。",
        "hotel": "{name}，{stars} 星，位于 {area}，每晚 ${price}。",
        "outbound": "去程", "inbound": "返程", "onward": "下一程", "stay": "入住：{start} 至 {end}。",
        "multi_intro": "以下是 {route} 的多城市行程：", "leg": "第 {index} 段：{origin} → {destination}（{date}）",
        "hotel_stay": "{city}：{start} 至 {end}", "no_results": "当前条件下没有找到可用选项，请调整地点、日期或预算后重试。",
        "partial": "部分行程没有匹配选项，以下列出已找到的结果。", "budget_title": "预算评估",
        "minimum": "当前最低可选总价：${total}（航班 ${flights}，酒店 ${hotels}）。",
        "subtotal": "已找到选项的小计：${total}（航班 ${flights}，酒店 ${hotels}）。",
        "within": "该行程符合 ${budget} 的总预算。", "shortfall": "最低可选费用超出总预算 ${amount}。",
        "incomplete": "部分航段或住宿缺少选项，暂时无法确认完整行程是否符合预算。",
        "recommendation": "推荐方案（{strategy}）", "closest": "最接近预算的方案（{strategy}）",
        "recommended_flight": "航班：{airline} {number}，{origin} → {destination}，${price}／人。",
        "recommended_hotel": "酒店：{name}，{city}，${price}／晚。",
        "recommended_total": "推荐组合预估总价：${total}。", "selected_subtotal": "已选方案小计：${total}。",
        "strategy_balanced": "均衡", "strategy_budget": "价格优先", "strategy_comfort": "舒适优先",
        "hotel_offer": "需要我为这次行程补充酒店选项吗？",
        "planning_details": "已记录目的地 {destination}。请提供出行日期、人数，并说明需要航班、酒店还是两者。",
        "scope": "请告诉我需要航班、酒店还是两者，以及目的地和日期。",
        "dates": "请提供出发日期及返程或退房日期。", "date_order": "返程或退房日期必须晚于出发或入住日期，请重新确认。",
        "date_year": "请提供包含年份的完整日期，格式为 YYYY-MM-DD。",
        "date_precision": "请确认准确的航班出发日期和酒店入住日期（YYYY-MM-DD）。",
        "origin": "请告诉我出发城市。", "destination": "请告诉我目的地。", "travellers": "请告诉我出行人数。",
        "hotel_dates": "请提供酒店入住和退房日期。", "multi_city_dates": "请提供每段旅程的日期，或开始日期及每个城市的停留天数。",
        "date_change": "请提供新的出发日期及返程或退房日期。",
        "unsupported": "目前没有 {locations} 的可用行程选项，请更换地点。",
        "decline_hotel": "好的，先只规划航班；如果需要酒店，随时告诉我。",
        "out_of_scope": "我可以帮助规划旅行、搜索航班和酒店。请告诉我你的旅行需求。",
        "general": "关于 {destination}，建议结合出行季节、天气、当地活动和住宿情况来安排。告诉我出行月份，我可以给出更具体的建议。",
        "tokyo_june": "东京六月通常温暖湿润，适合美食、购物、博物馆和城市漫步；建议带轻便雨具。",
        "tokyo_july": "东京七月较热且潮湿，适合节庆、美食和晚间活动；白天安排室内休息并注意补水。",
        "attractions": "可以考虑 {destination} 的热门景点，并根据停留天数安排路线。",
        "attractions_tokyo": "东京可考虑新宿、涩谷、浅草、上野、银座，以及箱根或日光一日游。",
        "attractions_singapore": "新加坡可考虑滨海湾花园、圣淘沙、鱼尾狮公园、植物园、牛车水和小印度。",
        "attractions_paris": "巴黎可考虑埃菲尔铁塔、卢浮宫、奥赛博物馆、蒙马特和凡尔赛宫。",
        "data_available": "系统可搜索的航班和酒店选项取决于具体城市与日期。请提供路线和出行时间。",
        "compare_intro": "根据当前多城市行程，可以这样比较：",
        "compare_tokyo": "东京适合体验寿司、拉面、居酒屋和夜间餐饮；新宿、涩谷等区域选择丰富。",
        "compare_singapore": "新加坡有熟食中心、娘惹菜和多元文化街区，品尝不同风味很方便。",
        "compare_paris": "巴黎适合咖啡馆、面包店、法式餐馆和美食市场。",
        "compare_history": "如果也重视历史景点，巴黎的博物馆和古迹尤其丰富。",
        "compare_nightlife": "如果也重视夜生活，东京更热闹；巴黎则适合文化活动与悠闲夜晚。",
        "more_info": "请补充目的地、日期，以及需要航班、酒店还是两者。",
    },
    "ja": {
        "intro": "{destination} の旅程候補です：", "flights": "航空券の候補", "hotels": "ホテルの候補",
        "flight": "{leg}：{airline} {number}、{origin} → {destination}、{date} {departure}–{arrival}、1人 ${price}。",
        "hotel": "{name}、{stars}つ星、{area}、1泊 ${price}。",
        "outbound": "往路", "inbound": "復路", "onward": "次の区間", "stay": "宿泊：{start}～{end}。",
        "multi_intro": "{route} の周遊プランです：", "leg": "区間 {index}：{origin} → {destination}（{date}）",
        "hotel_stay": "{city}：{start}～{end}", "no_results": "条件に合う候補がありません。目的地、日付、予算を変更してお試しください。",
        "partial": "一部の区間で候補が見つかりませんでした。見つかった候補を表示します。", "budget_title": "予算評価",
        "minimum": "利用可能な最安合計：${total}（航空券 ${flights}、ホテル ${hotels}）。",
        "subtotal": "見つかった候補の小計：${total}（航空券 ${flights}、ホテル ${hotels}）。",
        "within": "この旅程は総予算 ${budget} に収まります。", "shortfall": "最安の費用でも予算を ${amount} 超えます。",
        "incomplete": "一部の航空券または宿泊候補がないため、総予算内か確認できません。",
        "recommendation": "おすすめプラン（{strategy}）", "closest": "予算に最も近いプラン（{strategy}）",
        "recommended_flight": "航空券：{airline} {number}、{origin} → {destination}、1人 ${price}。",
        "recommended_hotel": "ホテル：{name}、{city}、1泊 ${price}。",
        "recommended_total": "おすすめの概算合計：${total}。", "selected_subtotal": "選択候補の小計：${total}。",
        "strategy_balanced": "バランス", "strategy_budget": "価格重視", "strategy_comfort": "快適さ重視",
        "hotel_offer": "この旅程にホテルも追加しますか？",
        "planning_details": "目的地 {destination} を記録しました。旅行日、人数、航空券とホテルのどちらが必要か教えてください。",
        "scope": "航空券、ホテル、または両方のどれが必要か、目的地と日付を教えてください。",
        "dates": "出発日と帰着日またはチェックアウト日を教えてください。", "date_order": "帰着日またはチェックアウト日は出発日より後にしてください。",
        "date_year": "年を含む日付を YYYY-MM-DD 形式で教えてください。",
        "date_precision": "正確な出発日とチェックイン日を YYYY-MM-DD 形式で確認してください。",
        "origin": "出発都市を教えてください。", "destination": "目的地を教えてください。", "travellers": "旅行人数を教えてください。",
        "hotel_dates": "チェックイン日とチェックアウト日を教えてください。", "multi_city_dates": "各区間の日付、または開始日と各都市の滞在日数を教えてください。",
        "date_change": "新しい出発日と帰着日またはチェックアウト日を教えてください。",
        "unsupported": "{locations} の候補は現在ありません。別の目的地をお試しください。",
        "decline_hotel": "承知しました。まず航空券のみを検討します。ホテルが必要になったらお知らせください。",
        "out_of_scope": "旅行計画、航空券、ホテルについてお手伝いできます。旅行の希望を教えてください。",
        "general": "{destination} への旅行は、季節、天候、現地イベント、宿泊状況を確認して計画するとよいでしょう。旅行月を教えていただければ、詳しくご案内します。",
        "tokyo_june": "東京の6月は暖かく湿度が高めです。食事、買い物、博物館、街歩きに向きます。雨具も用意してください。",
        "tokyo_july": "東京の7月は暑く湿度が高めです。祭りや夜の観光を楽しみ、日中は休憩と水分補給を心がけてください。",
        "attractions": "{destination} の人気スポットを、滞在日数に合わせて組み合わせるとよいでしょう。",
        "attractions_tokyo": "東京では新宿、渋谷、浅草、上野、銀座、箱根や日光への日帰り旅行が候補です。",
        "attractions_singapore": "シンガポールではガーデンズ・バイ・ザ・ベイ、セントーサ、マーライオン公園、植物園、チャイナタウン、リトル・インディアが候補です。",
        "attractions_paris": "パリではエッフェル塔、ルーブル美術館、オルセー美術館、モンマルトル、ベルサイユ宮殿が候補です。",
        "data_available": "検索できる航空券とホテルは都市と日付によって異なります。経路と旅行日程を教えてください。",
        "compare_intro": "現在の周遊ルートを比較すると：",
        "compare_tokyo": "東京では寿司、ラーメン、居酒屋、深夜の食事などを楽しめます。新宿や渋谷は選択肢が豊富です。",
        "compare_singapore": "シンガポールではホーカー料理、プラナカン料理、多文化地区の味を気軽に楽しめます。",
        "compare_paris": "パリはカフェ、パン屋、ビストロ、食品市場が魅力です。",
        "compare_history": "歴史的な名所も重視するなら、パリには博物館や史跡が豊富です。",
        "compare_nightlife": "ナイトライフなら東京は活気があり、パリは文化的で落ち着いた夜に向きます。",
        "more_info": "目的地、日付、航空券とホテルのどちらが必要か教えてください。",
    },
    "es": {
        "intro": "Estas son las opciones para {destination}:", "flights": "Vuelos", "hotels": "Hoteles",
        "flight": "{leg}: {airline} {number}, {origin} → {destination}, {date} {departure}–{arrival}, ${price} por persona.",
        "hotel": "{name}, {stars} estrellas, en {area}, ${price} por noche.",
        "outbound": "Ida", "inbound": "Vuelta", "onward": "Siguiente tramo", "stay": "Estancia: {start} a {end}.",
        "multi_intro": "Este es el itinerario para {route}:", "leg": "Tramo {index}: {origin} → {destination} ({date})",
        "hotel_stay": "{city}: {start} a {end}", "no_results": "No hay opciones para estas condiciones. Prueba otra ciudad, fecha o presupuesto.",
        "partial": "Faltan opciones para parte del viaje; se muestran las disponibles.", "budget_title": "Evaluación del presupuesto",
        "minimum": "Total mínimo disponible: ${total} (vuelos ${flights}; hoteles ${hotels}).",
        "subtotal": "Subtotal de opciones disponibles: ${total} (vuelos ${flights}; hoteles ${hotels}).",
        "within": "El viaje cabe en el presupuesto total de ${budget}.", "shortfall": "El costo mínimo supera el presupuesto en ${amount}.",
        "incomplete": "Faltan vuelos o estancias; no se puede confirmar el presupuesto del viaje completo.",
        "recommendation": "Plan recomendado ({strategy})", "closest": "Plan más cercano al presupuesto ({strategy})",
        "recommended_flight": "Vuelo: {airline} {number}, {origin} → {destination}, ${price} por persona.",
        "recommended_hotel": "Hotel: {name}, {city}, ${price} por noche.",
        "recommended_total": "Total estimado recomendado: ${total}.", "selected_subtotal": "Subtotal estimado: ${total}.",
        "strategy_balanced": "equilibrado", "strategy_budget": "menor costo", "strategy_comfort": "comodidad",
        "hotel_offer": "¿Quieres añadir hoteles a este viaje?",
        "planning_details": "He anotado el destino {destination}. Indica fechas, viajeros y si necesitas vuelos, hoteles o ambos.",
        "scope": "Dime si necesitas vuelos, hoteles o ambos, además del destino y las fechas.",
        "dates": "Indica la fecha de salida y la de regreso o salida del hotel.", "date_order": "La fecha de regreso o salida del hotel debe ser posterior a la de ida o entrada.",
        "date_year": "Indica la fecha completa con año en formato YYYY-MM-DD.",
        "date_precision": "Confirma las fechas exactas de salida y entrada al hotel en formato YYYY-MM-DD.",
        "origin": "Indica la ciudad de origen.", "destination": "Indica el destino.", "travellers": "Indica cuántas personas viajan.",
        "hotel_dates": "Indica las fechas de entrada y salida del hotel.", "multi_city_dates": "Indica las fechas de cada tramo, o la fecha inicial y los días en cada ciudad.",
        "date_change": "Indica las nuevas fechas de salida y regreso o salida del hotel.",
        "unsupported": "No hay opciones para {locations} por ahora. Prueba otro destino.",
        "decline_hotel": "De acuerdo, seguimos solo con vuelos. Avísame si después necesitas hotel.",
        "out_of_scope": "Puedo ayudarte a planificar viajes y buscar vuelos u hoteles. Cuéntame tu viaje.",
        "general": "Para {destination}, revisa la temporada, el clima, los eventos y la disponibilidad de alojamiento. Dime el mes para darte una orientación más concreta.",
        "tokyo_june": "Junio en Tokio suele ser cálido y húmedo; es adecuado para gastronomía, compras, museos y paseos. Lleva ropa para la lluvia.",
        "tokyo_july": "Julio en Tokio suele ser caluroso y húmedo. Disfruta los festivales y las actividades nocturnas, y descansa e hidrátate durante el día.",
        "attractions": "Puedes elegir lugares populares de {destination} según la duración del viaje.",
        "attractions_tokyo": "En Tokio puedes visitar Shinjuku, Shibuya, Asakusa, Ueno y Ginza, o hacer una excursión a Hakone o Nikko.",
        "attractions_singapore": "En Singapur puedes visitar Gardens by the Bay, Sentosa, Merlion Park, el jardín botánico, Chinatown y Little India.",
        "attractions_paris": "En París puedes visitar la Torre Eiffel, el Louvre, el Museo de Orsay, Montmartre y Versalles.",
        "data_available": "Los vuelos y hoteles disponibles dependen de la ciudad y la fecha. Indica la ruta y las fechas del viaje.",
        "compare_intro": "Para las ciudades de tu itinerario, esta es la comparación:",
        "compare_tokyo": "Tokio ofrece sushi, ramen, izakayas y comida nocturna; Shinjuku y Shibuya tienen muchas opciones.",
        "compare_singapore": "Singapur destaca por sus puestos de comida, la cocina peranakan y los barrios multiculturales.",
        "compare_paris": "París destaca por cafés, panaderías, bistrós y mercados gastronómicos.",
        "compare_history": "Si también buscas lugares históricos, París ofrece numerosos museos y monumentos.",
        "compare_nightlife": "Para la vida nocturna, Tokio es más animado; París ofrece veladas culturales y tranquilas.",
        "more_info": "Indica destino, fechas y si necesitas vuelos, hoteles o ambos.",
    },
}


def _line(language: str, key: str, **values: Any) -> str:
    return COPY[language][key].format(**values)


CITY_LABELS = {"TYO": "Tokyo", "SIN": "Singapore", "PAR": "Paris", "BKK": "Bangkok",
               "HKG": "Hong Kong", "SEL": "Seoul", "DXB": "Dubai", "LON": "London",
               "BLR": "Bengaluru", "MAA": "Chennai", "MEX": "Mexico City"}


def _city(value: Any) -> str:
    return CITY_LABELS.get(str(value), str(value or "—"))


def _general_reply(state: dict[str, Any], language: str) -> str:
    message = str(state.get("current_message", "")).lower()
    params = state.get("travel_params", {})
    destination = _city(params.get("destination"))
    english = str(state.get("message_to_show_user", ""))
    plan = state.get("multi_city_plan") or {}
    if "Based on your current itinerary" in english and plan.get("cities"):
        seen: list[str] = []
        for code in plan["cities"]:
            label = _city(code)
            if label not in seen:
                seen.append(label)
        parts = [_line(language, "compare_intro")]
        for label in seen:
            key = {"Tokyo": "compare_tokyo", "Singapore": "compare_singapore", "Paris": "compare_paris"}.get(label)
            if key:
                parts.append("- " + _line(language, key))
        if any(word in message for word in ("history", "historical", "heritage", "culture")):
            parts.append(_line(language, "compare_history"))
        if "nightlife" in message or "night life" in message:
            parts.append(_line(language, "compare_nightlife"))
        return "\n".join(parts)
    if "Tokyo" in english or destination == "TYO":
        destination = "Tokyo"
    elif "Singapore" in english or destination == "SIN":
        destination = "Singapore"
    elif "Paris" in english or destination == "PAR":
        destination = "Paris"
    if any(word in message for word in ("places", "attractions", "things to do", "must see", "where to visit")):
        key = {"Tokyo": "attractions_tokyo", "Singapore": "attractions_singapore", "Paris": "attractions_paris"}.get(destination, "attractions")
        return _line(language, key, destination=destination)
    if "mock data" in message or "available data" in message:
        return _line(language, "data_available")
    if destination == "Tokyo" and ("june" in message or "jun" in message):
        return _line(language, "tokyo_june")
    if destination == "Tokyo" and ("july" in message or "jul" in message):
        return _line(language, "tokyo_july")
    return _line(language, "general", destination=destination)


def _clarification_reply(state: dict[str, Any], language: str) -> str:
    intent = state.get("user_intent")
    pending = set(state.get("pending_clarifications") or [])
    extracted = state.get("extracted") or {}
    if intent == "decline_hotel":
        return _line(language, "decline_hotel")
    if intent == "out_of_scope":
        return _line(language, "out_of_scope")
    unsupported = extracted.get("_unsupported_locations") or []
    if unsupported:
        return _line(language, "unsupported", locations=", ".join(map(str, unsupported)))
    if "date_order" in pending:
        return _line(language, "date_order")
    if "date_year" in pending:
        return _line(language, "date_year")
    if "date_precision" in pending:
        return _line(language, "date_precision")
    if "date_change" in pending:
        return _line(language, "date_change")
    if "multi_city_dates" in pending:
        return _line(language, "multi_city_dates")
    if pending & {"travel_scope", "booking_scope", "travel_dates"}:
        destination = (state.get("travel_params") or {}).get("destination")
        if destination and "travel_scope" not in pending:
            return _line(language, "planning_details", destination=_city(destination))
        return _line(language, "scope")
    parts = [_line(language, key) for key in ("origin", "destination", "travellers", "hotel_dates") if key in pending]
    if "departure_date" in pending:
        parts.append(_line(language, "dates"))
    if parts:
        return " ".join(parts)
    english = str(state.get("message_to_show_user") or "").lower()
    if any(marker in english for marker in ("not available", "no matching", "could not find", "don't have matching")):
        return _line(language, "no_results")
    return _line(language, "more_info")


def _render_decision(state: dict[str, Any], language: str) -> list[str]:
    assessment = state.get("budget_assessment")
    recommendation = state.get("recommendation")
    if assessment is None or recommendation is None:
        return []
    lines = [f"\n**{_line(language, 'budget_title')}**"]
    lines.append(_line(language, "minimum" if assessment.is_complete else "subtotal",
                       total=f"{assessment.minimum_total_cost_usd:,}",
                       flights=f"{assessment.minimum_flight_cost_usd:,}",
                       hotels=f"{assessment.minimum_hotel_cost_usd:,}"))
    if assessment.total_budget_usd is not None:
        if assessment.within_budget is True:
            lines.append(_line(language, "within", budget=f"{assessment.total_budget_usd:,}"))
        elif assessment.shortfall_usd:
            lines.append(_line(language, "shortfall", amount=f"{assessment.shortfall_usd:,}"))
        else:
            lines.append(_line(language, "incomplete"))
    if assessment.missing_groups:
        lines.append(_line(language, "incomplete"))
    if recommendation.flights or recommendation.hotels:
        strategy = _line(language, f"strategy_{recommendation.strategy}")
        heading = "closest" if recommendation.within_budget is False else "recommendation"
        lines.append(f"\n**{_line(language, heading, strategy=strategy)}**")
        for item in recommendation.flights:
            option = item.option
            lines.append("- " + _line(language, "recommended_flight", airline=option.airline,
                                       number=option.flight_number, origin=option.origin,
                                       destination=option.destination, price=f"{option.price_usd:,}"))
        for item in recommendation.hotels:
            option = item.option
            lines.append("- " + _line(language, "recommended_hotel", name=option.hotel_name,
                                       city=option.city_name, price=f"{option.price_per_night_usd:,}"))
        lines.append(_line(language, "recommended_total" if recommendation.is_complete else "selected_subtotal",
                           total=f"{recommendation.estimated_total_usd:,}"))
    return lines


def render_response(state: dict[str, Any], language: str, english: str) -> str:
    """Return the current turn in the selected language; English remains unchanged."""
    if language not in COPY:
        return english
    route = state.get("route")
    if route == "general":
        return _general_reply(state, language)
    if route not in {"flight", "hotel", "both", "multi_city"}:
        return _clarification_reply(state, language)

    aggregated = state.get("final_aggregated_options") or {}
    params = state.get("travel_params") or {}
    lines: list[str] = []
    if route == "multi_city":
        plan = state.get("multi_city_plan") or {}
        cities = plan.get("cities") or []
        lines.append(_line(language, "multi_intro", route=" → ".join(_city(city) for city in cities)))
        itinerary = aggregated.get("multi_city") or {}
        for index, segment in enumerate(itinerary.get("flights", []), 1):
            lines.append(f"\n**{_line(language, 'leg', index=index, origin=segment.get('origin'), destination=segment.get('destination'), date=segment.get('departure_date'))}**")
            for option in segment.get("options", [])[:2]:
                lines.append("- " + _line(language, "flight", leg=_line(language, "outbound"),
                                           airline=option.airline, number=option.flight_number,
                                           origin=option.origin, destination=option.destination,
                                           date=option.departure_date, departure=option.departure_time,
                                           arrival=option.arrival_time, price=f"{option.price_usd:,}"))
        for segment in itinerary.get("hotels", []):
            lines.append(f"\n**{_line(language, 'hotel_stay', city=segment.get('destination'), start=segment.get('check_in_date'), end=segment.get('check_out_date'))}**")
            for option in segment.get("options", [])[:2]:
                lines.append("- " + _line(language, "hotel", name=option.hotel_name,
                                           stars=option.star_rating, area=option.area,
                                           price=f"{option.price_per_night_usd:,}"))
    else:
        flights = aggregated.get("flights") or []
        hotels = aggregated.get("hotels") or []
        if flights or hotels:
            lines.append(_line(language, "intro", destination=_city(params.get("destination"))))
        if flights:
            lines.append(f"\n**{_line(language, 'flights')}**")
            for option in flights[:4]:
                leg_key = "outbound" if option.trip_leg == "outbound" else "inbound"
                lines.append("- " + _line(language, "flight", leg=_line(language, leg_key),
                                           airline=option.airline, number=option.flight_number,
                                           origin=option.origin, destination=option.destination,
                                           date=option.departure_date, departure=option.departure_time,
                                           arrival=option.arrival_time, price=f"{option.price_usd:,}"))
        if hotels:
            lines.append(f"\n**{_line(language, 'hotels')}**")
            if params.get("check_in_date") and params.get("check_out_date"):
                lines.append(_line(language, "stay", start=params["check_in_date"], end=params["check_out_date"]))
            for option in hotels[:3]:
                lines.append("- " + _line(language, "hotel", name=option.hotel_name,
                                           stars=option.star_rating, area=option.area,
                                           price=f"{option.price_per_night_usd:,}"))
        if flights and not hotels and not params.get("needs_hotel"):
            lines.append("\n" + _line(language, "hotel_offer"))
    if aggregated.get("errors") or aggregated.get("partials") or aggregated.get("budget_warnings"):
        lines.append("\n" + _line(language, "partial" if lines else "no_results"))
    lines.extend(_render_decision(state, language))
    return "\n".join(lines).strip() or _line(language, "no_results")
