"""
LLM config: Tüm chat/LLM node'ları OpenAI (langchain_openai) kullanır.
Wiro sadece create_foto (görsel) ve create_video (Sora 2) Run API'de kullanılıyor.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_llm(temperature=0):
    """OpenAI chat modeli. MODEL_NAME ve OPENAI_API_KEY .env'den okunur."""
    return ChatOpenAI(
        temperature=temperature,
        model=os.getenv("MODEL_NAME"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def get_chat_model(temperature=0.3):
    """Grafik node'ları için chat modeli."""
    return get_llm(temperature=temperature)


