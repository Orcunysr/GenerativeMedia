"""
Üretilen reklam görselinden (veya aynı ürün/ortam bağlamından) kısa reklam filmi senaryosu yazar.
create_image_prompt mantığına benzer: state (ürün, poster ortamı, görsel prompt) → reklam filmi senaryosu.
"""
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from graph.config.llm import get_chat_model


def _state_to_str_for_video(state: dict[str, Any]) -> str:
    """Video senaryosu için state'ten ilgili alanları metin yapar."""
    parts = []
    if state.get("items_story"):
        parts.append(f"items_story: {state['items_story']}")
    if state.get("image_description"):
        parts.append(f"image_description: {state['image_description']}")
    if state.get("generated_image_prompt"):
        parts.append(f"generated_image_prompt (reklam görseli ortamı): {state['generated_image_prompt']}")
    if state.get("poster_image_address"):
        parts.append("poster_image_address: (reklam görseli üretildi)")
    if state.get("poster_promt"):
        parts.append(f"poster_promt: {state['poster_promt']}")
    if state.get("video_promt"):
        parts.append(f"video_promt: {state['video_promt']}")
    if state.get("user_prompt"):
        parts.append(f"user_prompt: {state['user_prompt']}")
    return "\n".join(parts) if parts else "(state empty)"


SYSTEM_PROMPT = """Sen bir reklam filmi senaryo yazarısın. Verilen ürün ve üretilmiş reklam görseli ortamına uygun, kısa ve GERÇEKÇİ bir reklam filmi senaryosu yazıyorsun.

Zorunlu kurallar:
- Senaryo 15–30 saniyelik kısa reklam için; ürün ve ortam üretilen görselle AYNI dünyada, aynı mekân ve ışıkta.
- Sadece doğal, gerçekçi hareketler: hafif kamera hareketi, ışığın hafif değişimi, ürünün sabit veya çok hafif hareketi. İnsan varsa sadece gerçekçi küçük hareketler (el, bakış).
- YASAK: Absürt, surreal, anlamsız veya gerçekdışı öğeler. Nesnelerin aniden belirmesi, uçması, deforme olması, mantıksız sahne geçişleri, fantastik efektler, komik veya tuhaf hareketler YOK.
- YASAK: Ortamın veya ürünün tutarsız değişmesi; farklı mekânlara atlama; anlamsız semboller veya metin.
- Reklam tonu: profesyonel, sade, ürün odaklı; dikkat çekici ama abartısız. Çıktıyı Türkçe ver; sahne betimlemeleri kısa ve net olsun."""

HUMAN_TEMPLATE = """Bağlam (ürün ve reklam görseli ortamı):

{state_text}

Bu ürün ve ortam için kısa bir reklam filmi senaryosu yaz (15–30 sn). Üretilen görseldeki ortam ve ürün aynı kalmalı; sadece hafif, doğal hareket ve ışık değişimi. Absürt veya surreal öğe ekleme; gerçekçi, profesyonel reklam stili. Türkçe çıktı ver."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", HUMAN_TEMPLATE),
])

llm = get_chat_model()

create_video_scenario_chain = (
    prompt_template
    | llm
    | StrOutputParser()
)


def create_video_scenario(state: dict[str, Any]) -> str:
    """
    State'ten (ürün, üretilmiş görsel promptu, poster bilgisi) reklam filmi senaryosu üretir.
    Grafte veya node'da: scenario = create_video_scenario(state)
    """
    state_text = _state_to_str_for_video(state)
    return create_video_scenario_chain.invoke({"state_text": state_text})
