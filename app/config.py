import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,     # mencegah koneksi timeout
        "pool_recycle": 280,       # membatasi masa koneksi
    }
    MAX_QUESTIONS_TO_STORE = int(os.getenv("MAX_QUESTIONS_TO_STORE", "1000"))
    QUIZ_USE_GEMINI_ALWAYS = os.getenv("QUIZ_USE_GEMINI_ALWAYS", "false").lower() in ("1","true","yes","on")
