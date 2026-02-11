"""Tavily web araması aracı. TAVILY_API_KEY .env'de olmalı."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from langchain_core.tools import tool

_wrapper = TavilySearchAPIWrapper()


def _tavily_run(query: str, max_results: int = 5) -> str:
    """Tavily araması yapar; API'den answer + results metin olarak döner."""
    try:
        raw = _wrapper.raw_results(
            query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
        )
        parts = []
        if raw.get("answer"):
            parts.append("Özet: " + raw["answer"])
        for i, r in enumerate(raw.get("results", [])[:max_results], 1):
            content = r.get("content", "").strip()
            url = r.get("url", "")
            title = r.get("title", "")
            if content:
                parts.append(f"[{i}] {title}\n{content}\nKaynak: {url}")
        return "\n\n".join(parts) if parts else "Sonuç bulunamadı."
    except Exception as e:
        return f"Arama hatası: {e}"


@tool
def tavily_search(query: str) -> str:
    """Web'de güncel bilgi arar. Soru veya arama terimini ver."""
    return _tavily_run(query)
