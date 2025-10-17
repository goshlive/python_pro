# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from dotenv import load_dotenv
from app.config import Config

db = SQLAlchemy()
csrf = CSRFProtect() 
login_manager = LoginManager()
login_manager.login_view = "main.login"

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app) 

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    @app.get("/healthz")
    def healthz():
        return "ok", 200

    with app.app_context():
        db.create_all()

        from .models import Topic
        # input default topik jika belum ada di database
        seed = [
            "Pengembangan kecerdasan buatan dalam Python",
            "Visi Komputer",
            "NLP (Pemrograman Neuro-linguistik)",
            "Menerapkan model AI ke dalam aplikasi Python",
        ]
        for name in seed:
            if not Topic.query.filter_by(name=name).first():
                db.session.add(Topic(name=name))
        db.session.commit()
        
        from .models import User
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    return app
