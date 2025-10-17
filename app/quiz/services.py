# app/quiz/services.py
from typing import Annotated
from pydantic import BaseModel, Field
from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class QuizItem(BaseModel):
    question: str
    # tampilkan 4 pilihan jawaban
    options: Annotated[list[str], Field(min_length=4, max_length=4)]
    # index jawaban yang benar [0..3]
    correct_index: Annotated[int, Field(ge=0, le=3)]

def generate_mcq(topic: str) -> QuizItem:
    prompt = (
        "Buat SATU soal pilihan ganda singkat tentang topik ini. "
        "Empat opsi, hanya satu benar. Bahasa Indonesia.\n\n"
        f"Topik: {topic}"
    )
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": QuizItem,
        },
    )
    return QuizItem.model_validate_json(resp.text)
