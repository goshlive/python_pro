# app/routes.py
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
)
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from . import db
from .forms import RegisterForm, LoginForm, ForgotPasswordForm
from .models import User, Question, Attempt
from app.quiz.services import generate_mcq
import json, os

# Blueprint untuk route utama
bp = Blueprint("main", __name__)

# Fungsi random
def _rand_func():
    dialect = db.session.get_bind().dialect.name
    return func.random() if dialect == "sqlite" else func.rand()

# Fungsi untuk mendapatkan topik berdasarkan topik id
def _get_topic_from_request():
    from .models import Topic

    topic_id = request.args.get("topic_id", type=int)
    if topic_id:
        t = Topic.query.get(topic_id)
        if t:
            return t
    return Topic.query.order_by(Topic.name.asc()).first()

# Route untuk halaman index
@bp.get("/")
def index():
    # If already logged in, go to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html", form=LoginForm())

# Route untuk halaman dashboard
@bp.get("/dashboard")
@login_required
def dashboard():
    from .models import Topic, User

    leaders = User.query.order_by(User.score_total.desc(), User.username.asc()).limit(50).all()

    topics = Topic.query.order_by(Topic.name.asc()).all()
    default_topic_id = topics[0].id if topics else None

    default_city = os.getenv("DEFAULT_CITY")
    return render_template(
        "dashboard.html",
        leaders=leaders,
        default_city=default_city,
        topics=topics,
        default_topic_id=default_topic_id,
    )

# Route untuk registerasi
@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data.strip(),
                email=form.email.data.strip().lower(),
                password_hash=generate_password_hash(form.password.data),
            )
            db.session.add(user)
            db.session.commit()
            flash("Akun telah berhasil dibuat! Anda bisa log in sekarang.", "success")
            return redirect(url_for("main.index"))
        except IntegrityError:
            db.session.rollback()
            flash("Username atau email sudah terpakai. Gunakan yang lain.", "danger")
    return render_template("register.html", form=form)

# Route untuk login
@bp.route("/login", methods=["POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash(f"Halo, {user.username}! Anda berhasil Log In.", "success")
            return redirect(url_for("main.index"))
        flash("Username atau password salah.", "danger")
    # Jika gagal, render ulang index.html dengan error + flash
    return render_template("index.html", form=form)

# Route untuk logout
@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah Log out.", "info")
    return redirect(url_for("main.index"))


# API untuk mendapatkan pertanyaan quiz berikutnya
@bp.get("/api/quiz/next")
@login_required
def api_quiz_next():
    from .models import Topic, Question

    cfg = current_app.config
    max_store = cfg.get("MAX_QUESTIONS_TO_STORE", 1000)
    always_gen = cfg.get("QUIZ_USE_GEMINI_ALWAYS", False)

    topic = _get_topic_from_request()
    if not topic:
        return jsonify({"error": "Topik tidak tersedia."}), 400

    def pick_random_existing():
        return Question.query.filter_by(topic_id=topic.id).order_by(_rand_func()).first()

    # Mode selalu GENERATE pertanyaan baru dari Gemini AI
    if always_gen:
        try:
            item = generate_mcq(topic.name)  # menghasilkan pertanyaan baru
            q = Question(
                topic_id=topic.id,
                question_text=item.question,
                options_json=json.dumps(item.options, ensure_ascii=False),
                correct_index=int(item.correct_index),
            )
            db.session.add(q)
            db.session.commit()
        except Exception:
            q = pick_random_existing()
            if not q:
                return jsonify({"error": "Gagal menghasilkan soal."}), 502
        return jsonify(
            {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "question_id": q.id,
                "question": q.question_text,
                "options": json.loads(q.options_json),
            }
        )

    # Normal mode: generate baru jika belum capai batas penyimpanan (sesuai konfigurasi MAX_QUESTIONS_TO_STORE di config.py)
    existing_count = Question.query.filter_by(topic_id=topic.id).count()
    if existing_count < max_store:
        try:
            item = generate_mcq(topic.name)
            q = Question(
                topic_id=topic.id,
                question_text=item.question,
                options_json=json.dumps(item.options, ensure_ascii=False),
                correct_index=int(item.correct_index),
            )
            db.session.add(q)
            db.session.commit()
        except Exception:
            q = pick_random_existing()
            if not q:
                return jsonify({"error": "Gagal menghasilkan soal."}), 502
    else:
        q = pick_random_existing()
        if not q:
            # Sebagai fallback, generate baru meskipun sudah capai batas
            item = generate_mcq(topic.name)
            q = Question(
                topic_id=topic.id,
                question_text=item.question,
                options_json=json.dumps(item.options, ensure_ascii=False),
                correct_index=int(item.correct_index),
            )
            db.session.add(q)
            db.session.commit()

    return jsonify(
        {
            "topic_id": topic.id,
            "topic_name": topic.name,
            "question_id": q.id,
            "question": q.question_text,
            "options": json.loads(q.options_json),
        }
    )

# API untuk submit jawaban quiz
@bp.post("/api/quiz/answer")
@login_required
def api_quiz_answer():
    data = request.get_json(silent=True) or {}
    qid = data.get("question_id")
    chosen = data.get("chosen_index")
    if qid is None or chosen is None:
        return jsonify({"error": "bad request"}), 400

    q = Question.query.get(int(qid))
    if not q:
        return jsonify({"error": "not found"}), 404

    is_correct = int(chosen) == int(q.correct_index)

    # Simpan attempt/jawaban ke database
    att = Attempt(
        user_id=current_user.id,
        question_id=q.id,
        chosen_index=int(chosen),
        is_correct=is_correct,
    )
    db.session.add(att)
    if is_correct:
        current_user.score_total = (current_user.score_total or 0) + 1
    db.session.commit()

    return jsonify(
        {
            "correct": is_correct,
            "correct_index": int(q.correct_index),
            "new_score": int(current_user.score_total),
        }
    )

# API untuk mendapatkan rating Skor user tertinggi
@bp.get("/api/leaderboard")
@login_required
def api_leaderboard():
    leaders = User.query.order_by(User.score_total.desc(), User.username.asc()).limit(50).all()
    return jsonify({"leaders": [{"username": u.username, "score": int(u.score_total or 0)} for u in leaders]})

# API untuk mendapatkan daftar topik
@bp.get("/api/topics")
@login_required
def api_topics():
    from .models import Topic

    topics = Topic.query.order_by(Topic.name.asc()).all()
    current_app.logger.info("api_topics -> %d topics: %s", len(topics), [(t.id, t.name) for t in topics])
    return jsonify({"topics": [{"id": t.id, "name": t.name} for t in topics]})

# Route untuk lupa password
@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    # Jika sudah login, re-direct ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        u = User.query.filter_by(username=form.username.data.strip()).first()
        if not u:
            flash("Username tidak ditemukan.", "danger")
            return render_template("forgot.html", form=form)

        u.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash("Password berhasil di-reset. Silakan login dengan password baru.", "success")
        return redirect(url_for("main.index"))

    return render_template("forgot.html", form=form)

