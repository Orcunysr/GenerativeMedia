"""
Yüklenen fotoğrafı (state'teki ilk görsel) vision modeli ile betimler.
Model: graph.config.llm (OpenAI). Çıktı create_image_prompt'ta kullanılır.
"""
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from graph.chains.create_foto import get_first_image_data_url
from graph.config.llm import get_chat_model


SYSTEM_DESCRIBE = """You are a product/advertising image analyst. Describe the PRODUCT in the given photo so it can be locked for downstream image generation — the output image must show this exact same product.

Write in English, one paragraph. Include:
- Brand name and product name (as read from the label, e.g. EMBEAUTY, Volumizing Care Shampoo).
- Product type (shampoo, lotion, etc.) and packaging: bottle shape, cap color, label color and main text/bands on it.
- Main colors (bottle, label, cap).
- Set info if present (e.g. 2-piece set, 400ml).

This text is the key so that only this product appears in the generated image; no other brand or product should be drawn. Output only the product description."""


def _describe_with_openai(image_data_url: str) -> Optional[str]:
    try:
        llm = get_chat_model(temperature=0)
        messages = [
            SystemMessage(content=SYSTEM_DESCRIBE),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Describe this photo according to the instructions above."},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ]
            ),
        ]
        out = llm.invoke(messages)
        return (out.content or "").strip() if out else None
    except Exception:
        return None


def describe_image_from_state(state: dict[str, Any]) -> str:
    """
    State'teki ilk yüklenen fotoğrafı (user_image_address / items_image_address) alır,
    vision ile betimler. Açıklama prompt üretiminde kullanılır.
    OPENAI_API_KEY yoksa: items_story varsa onu döndür (ürün kimliği prompt'ta kullanılır), yoksa genel metin.
    """
    image_url = get_first_image_data_url(state)
    if not image_url:
        # Görsel yok ama items_story varsa (örn. URL'den) onu kullan
        story = (state.get("items_story") or "").strip()
        if story:
            return f"Product in the reference image: {story}"
        return "Reference image not available; describe only environment, lighting, and style for product photography."
    desc = _describe_with_openai(image_url)
    if desc:
        return desc
    # Vision yok: items_story ile ürün kimliğini ver ki prompt'ta "ne çizilecek" belli olsun
    story = (state.get("items_story") or "").strip()
    if story:
        return f"Product in the reference image: {story}. Same product must appear in the output; only change environment and lighting."
    return "Reference product or user photo provided. Use it as the main subject; describe only the environment, background, and lighting for the new image."
