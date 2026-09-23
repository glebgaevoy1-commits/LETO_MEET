from flask import Flask, jsonify, render_template, request
from dataclasses import dataclass, asdict
from typing import Optional

app = Flask(__name__)


# -----------------------------
# Data model
# -----------------------------

@dataclass
class Event:
    id: int
    title: str
    summary: str
    description: str
    activity: str
    type: str
    duration: str
    place: str
    room: str
    date: str
    time: str
    end: str
    regular: bool
    organizer: str
    count: int = 0
    chat: str = ""
    contact: str = ""


# Temporary in-memory data.
# Later this list can be replaced with a database.
events = [
    Event(
        id=1,
        title="Погамать в доту на чилле",
        summary="Собираем команду на пару каток, йоу",
        description="Соберёмся на часок, спокойно погамаем. Зовите всех, кого знаете, мне одному плохо.\n\nНоутбук и наушники сами берите. Вопросы в чат пж",
        activity="Компьютерные игры",
        type="Просто сбор",
        duration="Пара часов",
        place="8 дом",
        room="Гостиная на 2 этаже",
        date="2026-09-19",
        time="17:00",
        end="19:00",
        regular=False,
        organizer="Михаил",
        count=4,
    ),
    Event(
        id=2,
        title="Настолки после уроков",
        summary="«Кодовые имена», «Каркассон» и то, что принесёте с собой.",
        description="Выберем игру на месте: монополия, манчкин и тд. Кто правил не знает - научим, без б.\n\nЕсли есть своя настолка, приносите! :D",
        activity="Настольные игры",
        type="Просто сбор",
        duration="Пара часов",
        place="9 дом",
        room="Гостиная, 1 этаж",
        date="2026-09-19",
        time="18:00",
        end="20:00",
        regular=False,
        organizer="Аня Гречкина",
        count=7,
    ),
    Event(
        id=3,
        title="Dota 2. Турнир",
        summary="Турнир по командам. можно без команды, подберём.",
        description="команд 3-5 будет. всё остальное обсудим в чате.",
        activity="Компьютерные игры",
        type="Турнир",
        duration="Более 5 часов",
        place="Li4",
        room="201",
        date="2026-09-20",
        time="12:00",
        end="18:00",
        regular=False,
        organizer="Иван Преображенский",
        count=12,
    ),
    Event(
        id=4,
        title="Порисульки :>",
        summary="Скетчбуки, карандаши и полчаса для своих идей, ну не вайбик ли (❁´◡`❁)",
        description="Небольшая встреча для тех, кто хочет порисовать в компании, общей темы нет, а может будет - каждый рисует своё или нет.\n\nЖелательно возьмите свои скетчбуки, материалы, но так-то бумага будет у нас).",
        activity="Рисование",
        type="Просто сбор",
        duration="Менее часа",
        place="Школа",
        room="AS1",
        date="2026-09-21",
        time="16:30",
        end="20:00",
        regular=True,
        organizer="Соня :>>",
        count=3,
    ),
    Event(
        id=5,
        title="Партия в шахматы",
        summary="Играем, разбираем позиции и учимся друг у друга.",
        description="Приходите несмотря на рейтинг. Найдём соперника и при желании разберём партию вместе.",
        activity="Настольные игры",
        type="Клуб",
        duration="Менее часа",
        place="Школа",
        room="Библиотека, общий зал",
        date="2026-09-22",
        time="17:00",
        end="18:30",
        regular=True,
        organizer="Владимир",
        count=6,
    ),
    Event(
        id=6,
        title="Прогулка после ужина",
        summary="Пару кругов по территории и разговоры обо всём и не о чём, о возвышенным и о повседневном.",
        description="Собираемся у южного выхода. Если будет дождь, на балкончиках соберёмся",
        activity="Прогулка",
        type="Просто сбор",
        duration="Менее часа",
        place="Улица",
        room="У главного входа",
        date="2026-09-23",
        time="19:30",
        end="20:00",
        regular=False,
        organizer="Таисия",
        count=5,
    ),
]


FILTER_GROUPS = [
    {
        "key": "activity",
        "label": "Род деятельности",
        "options": ["Компьютерные игры", "Настольные игры", "Рисование", "Прогулка"],
    },
    {
        "key": "type",
        "label": "Тип события",
        "options": ["Просто сбор", "Турнир", "Клуб"],
    },
    {
        "key": "duration",
        "label": "Длительность",
        "options": ["Буквально 15 минут", "Менее часа", "Около часа", "Пара часов", "Более 5 часов"],
    },
    {
        "key": "place",
        "label": "Место",
        "options": ["1 дом", "2 дом", "5 дом", "6 дом", "7 дом", "8 дом", "9 дом", "10 дом", "Li4", "Библиотека", "Южный вход"],
    },
]


# -----------------------------
# Helpers
# -----------------------------

def find_event(event_id: int) -> Optional[Event]:
    return next((event for event in events if event.id == event_id), None)


def filter_events(items, args):
    """Server-side filtering. The frontend also filters for instant UX."""
    result = list(items)

    for group in FILTER_GROUPS:
        selected = args.getlist(group["key"])
        if selected:
            result = [event for event in result if getattr(event, group["key"]) in selected]

    date_from = args.get("from", "")
    date_to = args.get("to", "")

    if date_from:
        result = [event for event in result if event.date >= date_from]
    if date_to:
        result = [event for event in result if event.date <= date_to]

    return sorted(result, key=lambda event: event.date + event.time)


# -----------------------------
# Pages
# -----------------------------

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/events")
def events_page():
    return render_template("index.html")


@app.get("/events/<int:event_id>")
def event_page(event_id):
    # The SPA handles the visual page. This endpoint is kept for normal
    # Flask navigation/API compatibility.
    if find_event(event_id) is None:
        return "Event not found", 404
    return render_template("index.html")


@app.get("/map")
def map_page():
    # Map UI can be added to the same frontend later.
    return render_template("index.html")


# -----------------------------
# API
# -----------------------------

@app.get("/api/events")
def api_events():
    filtered = filter_events(events, request.args)
    return jsonify([asdict(event) for event in filtered])


@app.get("/api/events/<int:event_id>")
def api_event(event_id):
    event = find_event(event_id)
    if event is None:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(asdict(event))


@app.get("/api/filter-groups")
def api_filter_groups():
    return jsonify(FILTER_GROUPS)


@app.post("/api/events")
def api_create_event():
    """
    Creates an event in memory.
    Replace this with database persistence and moderation later.
    """
    data = request.get_json(silent=True) or {}

    required = [
        "title", "summary", "description", "activity", "type",
        "duration", "place", "room", "date", "time", "end", "organizer"
    ]

    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return jsonify({"error": "Не заполнены обязательные поля", "fields": missing}), 400

    if data["end"] <= data["time"]:
        return jsonify({"error": "Окончание должно быть позже начала"}), 400

    next_id = max((event.id for event in events), default=0) + 1

    event = Event(
        id=next_id,
        title=str(data["title"]).strip(),
        summary=str(data.get("summary", "")).strip(),
        description=str(data["description"]).strip(),
        activity=str(data["activity"]).strip(),
        type=str(data["type"]).strip(),
        duration=str(data["duration"]).strip(),
        place=str(data["place"]).strip(),
        room=str(data["room"]).strip(),
        date=str(data["date"]).strip(),
        time=str(data["time"]).strip(),
        end=str(data["end"]).strip(),
        regular=bool(data.get("regular", False)),
        organizer=str(data["organizer"]).strip(),
        count=0,
        chat=str(data.get("chat", "")).strip(),
        contact=str(data.get("contact", "")).strip(),
    )

    events.append(event)
    return jsonify(asdict(event)), 201


if __name__ == "__main__":
    app.run(debug=True)
