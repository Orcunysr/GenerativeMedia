"""
Linkten çekilen ham metni (url_content, items_story) LLM ile 2–3 cümlelik,
okunabilir ürün açıklamasına çevirir. Tema ekranında fotoğraf altında gösterilir.
"""
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from graph.config.llm import get_chat_model

SYSTEM = """Sen bir e-ticaret asistanısın. Verilen ham ürün sayfası metninden sadece ÜRÜN bilgisini çıkarıp 2-3 cümlelik kısa bir açıklama yazıyorsun.

Kurallar:
- Sadece ürün adı, özellikleri, fiyat (varsa) gibi bilgileri kullan. Menü, "Ana içeriğe git", "Çekilişe katıl", "AI Ürün Bulucu" gibi site metinlerini ASLA yazma.
- Türkçe, doğal ve okunabilir yaz. Alıntı veya liste kullanma; düz paragraf.
- Çıktı sadece açıklama metni olsun, başka ekleme."""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "Ham sayfa / ürün metni:\n{raw_text}\n\nBu ürün için 2-3 cümlelik kısa açıklama yaz (Türkçe):"),
])

llm = get_chat_model(temperature=0.2)
chain = PROMPT | llm | StrOutputParser()


def get_product_description_llm(state: dict[str, Any]) -> str:
    """
    State'teki url_content ve items_story'den LLM ile kısa ürün açıklaması üretir.
    Boş veya hata durumunda ham items_story'nin ilk 400 karakteri döner.
    """
    raw_parts = []
    for key in ("items_story", "url_content"):
        v = state.get(key)
        if v and isinstance(v, str) and v.strip():
            raw_parts.append(v.strip())
    raw_text = "\n\n".join(raw_parts)[:6000]
    if not raw_text:
        return ""
    try:
        out = chain.invoke({"raw_text": raw_text})
        return (out or "").strip()[:500]
    except Exception:
        return (raw_parts[0] or "")[:400]
