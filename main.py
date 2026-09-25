from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)  # Keep it named exactly "app"

# -----------------------------
# Database Setup
# -----------------------------

# Secure environment check
database_url = os.environ.get('DATABASE_URL')

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add engine options here to prevent Vercel connection exhaustion
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)


# -----------------------------
# Data model
# -----------------------------

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    summary = db.Column(db.String(300), nullable=True)
    description = db.Column(db.Text, nullable=False)
    activity = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    place = db.Column(db.String(100), nullable=False)
    room = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False) 
    end = db.Column(db.String(10), nullable=False)
    regular = db.Column(db.Boolean, default=False)
    organizer = db.Column(db.String(100), nullable=False)
    count = db.Column(db.Integer, default=0)
    chat = db.Column(db.String(200), default="")
    contact = db.Column(db.String(200), default="")

    def to_dict(self):
        """Converts the SQL row into a regular dictionary for the API responses"""
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "description": self.description,
            "activity": self.activity,
            "type": self.type,
            "duration": self.duration,
            "place": self.place,
            "room": self.room,
            "date": self.date,
            "time": self.time,
            "end": self.end,
            "regular": self.regular,
            "organizer": self.organizer,
            "count": self.count,
            "chat": self.chat,
            "contact": self.contact
        }

# Automatically build database tables when the app runs
with app.app_context():
    db.create_all()


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

def filter_events(query_base, args):
    """Server-side filtering translated to SQL queries."""
    for group in FILTER_GROUPS:
        selected = args.getlist(group["key"])
        if selected:
            query_base = query_base.filter(getattr(Event, group["key"]).in_(selected))

    date_from = args.get("from", "")
    date_to = args.get("to", "")

    if date_from:
        query_base = query_base.filter(Event.date >= date_from)
    if date_to:
        query_base = query_base.filter(Event.date <= date_to)

    return query_base.order_by(Event.date, Event.time).all()


# -----------------------------
# Pages (FIX #2: Cleaned up overlapped routing decorators)
# -----------------------------

@app.get('/favicon.ico')
def favicon():
    return '', 204

@app.get("/")
@app.get("/events")
@app.get("/events/<int:event_id>")
@app.get("/map")
def index_pages(event_id=None):
    return render_template("index.html")


# -----------------------------
# API
# -----------------------------

@app.get("/api/events")
def api_events():
    filtered = filter_events(Event.query, request.args)
    return jsonify([event.to_dict() for event in filtered])

@app.get("/api/events/<int:event_id>")
def api_event(event_id):
    event = Event.query.get(event_id)
    if event is None:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event.to_dict())

@app.get("/api/filter-groups")
def api_filter_groups():
    return jsonify(FILTER_GROUPS)

@app.post("/api/events")
def api_create_event():
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

    new_event = Event(
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
        contact=str(data.get("contact", "")).strip()
    )

    db.session.add(new_event)
    db.session.commit()

    return jsonify(new_event.to_dict()), 201

if __name__ == "__main__":
    app.run(debug=True)