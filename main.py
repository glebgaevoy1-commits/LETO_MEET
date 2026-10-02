from flask import Flask, jsonify, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
import smtplib
import secrets
import os

app = Flask(__name__)  # Keep it named exactly "app"

# -----------------------------
# Database Setup
# -----------------------------
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is not configured")

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


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="user"
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role
        }


class AuthCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(150),
        nullable=False
    )

    username = db.Column(
        db.String(80),
        nullable=True
    )

    purpose = db.Column(
        db.String(20),
        nullable=False
    )

    code_hash = db.Column(
        db.String(255),
        nullable=False
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )


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
ALLOWED_DOMAINS = (
    "@student.letovo.ru",
    "@letovo.ru"
)

CODE_LIFETIME_MINUTES = 10


def normalize_email(email):
    return str(email or "").strip().lower()


def valid_letovo_email(email):
    return email.endswith(ALLOWED_DOMAINS)


def ensure_admin():
    admin_email = normalize_email(
        os.environ.get("ADMIN_EMAIL", "")
    )

    if not admin_email:
        return

    admin_name = os.environ.get(
        "ADMIN_NAME",
        "LETOMEET Admin"
    )

    user = User.query.filter_by(
        email=admin_email
    ).first()

    if not user:
        user = User(
            username=admin_name,
            email=admin_email,
            role="admin"
        )

        db.session.add(user)

    else:
        user.role = "admin"

    db.session.commit()


with app.app_context():
    db.create_all()
    ensure_admin()


def create_code():
    return f"{secrets.randbelow(1000000):06d}"


def send_email_code(email, code, purpose):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    email_from = os.environ.get("EMAIL_FROM", smtp_user)

    if not smtp_host or not smtp_user or not smtp_password:
        # Удобно для локальной разработки.
        # В production SMTP должен быть настроен.
        print(f"[LETOMEET DEV] Code for {email}: {code}")
        return True

    message = EmailMessage()

    message["Subject"] = (
        "Код для LETOMEET"
        if purpose == "login"
        else "Код регистрации в LETOMEET"
    )

    message["From"] = email_from
    message["To"] = email

    message.set_content(
        f"""Здравствуйте!

Ваш код для LETOMEET:

{code}

Код действует {CODE_LIFETIME_MINUTES} минут.

Если вы не запрашивали этот код, просто проигнорируйте это письмо.

LETOMEET
"""
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    return True


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def admin_required():
    user = current_user()

    if not user:
        return None, (
            jsonify({"error": "Необходимо войти"}),
            401
        )

    if user.role != "admin":
        return None, (
            jsonify({"error": "Доступ запрещён"}),
            403
        )

    return user, None

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


@app.post("/api/auth/register/request")
def register_request():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    email = normalize_email(data.get("email"))

    if not username:
        return jsonify({
            "error": "Введите имя"
        }), 400

    if len(username) > 80:
        return jsonify({
            "error": "Имя слишком длинное"
        }), 400

    if not valid_letovo_email(email):
        return jsonify({
            "error": "Используйте почту @student.letovo.ru или @letovo.ru"
        }), 400

    existing = User.query.filter_by(email=email).first()

    if existing:
        return jsonify({
            "error": "Этот email уже зарегистрирован. Войдите в аккаунт."
        }), 400

    code = create_code()

    auth_code = AuthCode(
        email=email,
        username=username,
        purpose="register",
        code_hash=generate_password_hash(code),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=CODE_LIFETIME_MINUTES)
    )

    db.session.add(auth_code)
    db.session.commit()

    try:
        send_email_code(email, code, "register")
    except Exception:
        db.session.delete(auth_code)
        db.session.commit()

        return jsonify({
            "error": "Не удалось отправить письмо. Попробуйте ещё раз."
        }), 500

    return jsonify({
        "message": "Код отправлен на вашу почту"
    })

@app.post("/api/auth/register/verify")
def register_verify():
    data = request.get_json(silent=True) or {}

    email = normalize_email(data.get("email"))
    code = str(data.get("code", "")).strip()

    if not valid_letovo_email(email):
        return jsonify({
            "error": "Некорректная почта"
        }), 400

    if not code.isdigit() or len(code) != 6:
        return jsonify({
            "error": "Введите 6-значный код"
        }), 400

    auth_code = (
        AuthCode.query
        .filter_by(
            email=email,
            purpose="register"
        )
        .order_by(AuthCode.id.desc())
        .first()
    )

    if not auth_code:
        return jsonify({
            "error": "Код не найден. Запросите новый."
        }), 400

    now = datetime.now(timezone.utc)

    if auth_code.expires_at.replace(tzinfo=timezone.utc) < now:
        return jsonify({
            "error": "Код истёк. Запросите новый."
        }), 400

    if not check_password_hash(
        auth_code.code_hash,
        code
    ):
        return jsonify({
            "error": "Неверный код"
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "Этот email уже зарегистрирован."
        }), 400

    user = User(
        username=auth_code.username,
        email=email,
        role="user"
    )

    db.session.add(user)
    db.session.delete(auth_code)
    db.session.commit()

    session["user_id"] = user.id

    return jsonify({
        "message": "Регистрация завершена",
        "user": user.to_dict()
    })

@app.post("/api/auth/login/request")
def login_request():
    data = request.get_json(silent=True) or {}

    email = normalize_email(data.get("email"))

    if not valid_letovo_email(email):
        return jsonify({
            "error": "Используйте почту @student.letovo.ru или @letovo.ru"
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "error": "Аккаунт не найден. Сначала зарегистрируйтесь."
        }), 404

    code = create_code()

    auth_code = AuthCode(
        email=email,
        username=user.username,
        purpose="login",
        code_hash=generate_password_hash(code),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=CODE_LIFETIME_MINUTES)
    )

    db.session.add(auth_code)
    db.session.commit()

    try:
        send_email_code(email, code, "login")
    except Exception:
        db.session.delete(auth_code)
        db.session.commit()

        return jsonify({
            "error": "Не удалось отправить письмо. Попробуйте ещё раз."
        }), 500

    return jsonify({
        "message": "Код отправлен на вашу почту"
    })

@app.post("/api/auth/login/verify")
def login_verify():
    data = request.get_json(silent=True) or {}

    email = normalize_email(data.get("email"))
    code = str(data.get("code", "")).strip()

    auth_code = (
        AuthCode.query
        .filter_by(
            email=email,
            purpose="login"
        )
        .order_by(AuthCode.id.desc())
        .first()
    )

    if not auth_code:
        return jsonify({
            "error": "Код не найден. Запросите новый."
        }), 400

    now = datetime.now(timezone.utc)

    if auth_code.expires_at.replace(tzinfo=timezone.utc) < now:
        return jsonify({
            "error": "Код истёк. Запросите новый."
        }), 400

    if not check_password_hash(
        auth_code.code_hash,
        code
    ):
        return jsonify({
            "error": "Неверный код"
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "error": "Пользователь не найден"
        }), 404

    db.session.delete(auth_code)
    db.session.commit()

    session["user_id"] = user.id

    return jsonify({
        "message": "Вход выполнен",
        "user": user.to_dict()
    })

@app.get("/api/auth/me")
def auth_me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "user": None
        })

    user = db.session.get(User, user_id)

    if not user:
        session.clear()

        return jsonify({
            "user": None
        })

    return jsonify({
        "user": user.to_dict()
    })

@app.post("/api/auth/logout")
def logout():
    session.clear()

    return jsonify({
        "message": "Вы вышли из аккаунта"
    })

@app.get("/api/admin/users")
def admin_users():
    user, error = admin_required()

    if error:
        return error

    users = User.query.order_by(
        User.created_at.desc()
    ).all()

    return jsonify({
        "users": [
            user.to_dict()
            for user in users
        ]
    })

@app.get("/api/admin/stats")
def admin_stats():
    user, error = admin_required()

    if error:
        return error

    return jsonify({
        "users": User.query.count(),
        "admins": User.query.filter_by(
            role="admin"
        ).count()
    })

if __name__ == "__main__":
    app.run(debug=True)