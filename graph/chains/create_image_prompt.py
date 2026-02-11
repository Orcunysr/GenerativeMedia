"""
State'ten ürün görseli için image-generation prompt'u üretir.
Örn. fotoda sadece boş bir şişe varsa, bu ürün için reklam kalitesinde bir foto prompt'u çıkarır.
"""
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from graph.config.llm import get_chat_model


def _state_to_str(state: dict[str, Any]) -> str:
    """State'i prompt için kısa metin yapar. image_description varsa öncelikle onu kullanır (fotoğrafa göre prompt)."""
    parts = []
    # Önce yüklenen fotoğrafın betimlemesi — prompt buna göre üretilir
    image_desc = state.get("image_description")
    if image_desc and str(image_desc).strip():
        parts.append(f"image_description (reference photo content):\n{image_desc}")
    for k in ("items_story", "url_content", "user_prompt", "poster_promt", "video_promt", "items_quality", "question"):
        v = state.get(k)
        if v is not None and str(v).strip():
            parts.append(f"{k}: {v!s}"[:500])
    if state.get("items_image_address"):
        parts.append("items_image_address: (product image available)")
    if state.get("user_image_address"):
        parts.append("user_image_address: (user photo available)")
    return "\n".join(parts) if parts else "(state empty)"


system_prompt = """You write prompts for image-to-image generation. The reference photo is sent to the model. The output image MUST show the EXACT SAME product as in the reference (same brand, same bottle, same label) — only the environment/setting changes.

TASK: Describe ONLY the **creative, lifestyle environment** (setting, surface, atmosphere). Do NOT describe the product; the reference image and image_description define it. The product in the output must be identical to the reference.

Prefer creative, realistic settings such as:
- Bathroom: sink edge (lavabo kenarı), marble counter next to sink, shelf above basin, clean tiles.
- Kitchen: marble or wood counter, next to a plant or fruit, soft morning light.
- Lifestyle: marble surface, fabric (towel, linen), soft shadows, natural or warm light.
- Premium: stone/marble plinth, soft gradient or blurred background, one clear surface with reflection.

Include:
- **Setting:** Concrete, creative place (e.g. "on a white marble sink ledge", "bathroom counter by a modern sink", "marble surface with a soft towel beside it").
- **Lighting:** Natural or soft studio light fitting that setting; subtle shadows.
- **Style:** High-end product photography, shallow depth of field, the product clearly in focus; environment slightly softer.

CRITICAL: Do NOT describe the product itself (reference defines it). Do NOT suggest other product types. Output a single paragraph in **English**, only the prompt text. No quotes."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Context (reference photo description and/or product info):\n{state_text}\n\nWrite the image-generation prompt for a creative, lifestyle ENVIRONMENT only (e.g. sink edge, bathroom counter, marble surface — not a flat studio). Product and colors stay the same; only the setting and lighting change. Single paragraph, English:"),
])

llm = get_chat_model()

# Chain: state (dict) -> state_text -> LLM -> prompt string
create_image_prompt_chain = (
    prompt_template
    | llm
    | StrOutputParser()
)


def create_image_prompt(state: dict[str, Any]) -> str:
    """
    State'ten ürün görseli için image-generation prompt'u üretir.
    user_selected_prompt varsa onu döndürür; yoksa tek prompt üretir.
    """
    if state.get("user_selected_prompt"):
        return (state.get("user_selected_prompt") or "").strip()
    state_text = _state_to_str(state)
    return create_image_prompt_chain.invoke({"state_text": state_text})


# --- 5 farklı prompt (URL + isteğe bağlı kullanıcı teması; kullanıcıya sunulur) ---
FIVE_PROMPTS_SYSTEM = """You write prompts for product image generation. The product is defined by the context (items_story, url_content). If the user gave a theme or style (user_prompt, poster_promt), use it: all 5 prompts should fit that theme (e.g. "kumsal" → beach, sand, summer; "minimalist" → clean, simple surfaces). If no theme is given, use varied creative settings.

Output MUST describe only the ENVIRONMENT/setting — same product, different creative settings. Output exactly 5 different prompts, one per line:
1. <first prompt paragraph>
2. <second prompt paragraph>
3. <third prompt paragraph>
4. <fourth prompt paragraph>
5. <fifth prompt paragraph>

Each prompt: one paragraph, English, creative lifestyle setting. Do NOT describe the product. If user theme exists, vary within that theme (e.g. beach: shore, towel, sunset, poolside). If no theme, vary widely (bathroom, kitchen, marble, morning light, luxury shelf)."""

five_prompts_template = ChatPromptTemplate.from_messages([
    ("system", FIVE_PROMPTS_SYSTEM),
    ("human", "Product/context:\n{state_text}\n\nWrite 5 different image-generation prompts (environment only). Number them 1. to 5."),
])

create_5_prompts_chain = five_prompts_template | llm | StrOutputParser()


def _parse_numbered_prompts(text: str) -> list[str]:
    """Metinden 1. 2. 3. 4. 5. ile başlayan paragrafları çıkarır."""
    import re
    prompts = []
    # 1. ... 2. ... veya 1) ... 2) ...
    parts = re.split(r"\n\s*(?:\d+[.)]\s*)", "\n" + (text or "").strip())
    for p in parts:
        p = p.strip()
        if not p or len(p) < 20:
            continue
        prompts.append(p.strip())
    if len(prompts) >= 5:
        return prompts[:5]
    if len(prompts) > 0:
        return prompts
    # Fallback: satır satır al (en fazla 5)
    lines = [s.strip() for s in (text or "").split("\n") if s.strip() and len(s.strip()) > 25]
    return lines[:5]


def create_5_prompt_options(state: dict[str, Any]) -> list[str]:
    """URL/ürün bilgisinden 5 farklı poster prompt'u üretir. Kullanıcıya sunulur."""
    state_text = _state_to_str(state)
    raw = create_5_prompts_chain.invoke({"state_text": state_text})
    return _parse_numbered_prompts(raw)


# --- LLM ile 5 seçenekten en iyisini otomatik seç ---
PICK_BEST_SYSTEM = """You are choosing the best ad poster prompt for a product. Given the product context and 5 candidate prompts (each describes a lifestyle environment for the same product), pick the ONE that will work best for a professional ad: most appealing, on-brand, and suitable for the product type. Consider: relevance to product category (e.g. skincare → bathroom/premium), visual appeal, and clarity. Reply with ONLY a single digit from 1 to 5, nothing else."""

pick_best_template = ChatPromptTemplate.from_messages([
    ("system", PICK_BEST_SYSTEM),
    ("human", "Product context:\n{context}\n\nPrompts:\n1. {p1}\n2. {p2}\n3. {p3}\n4. {p4}\n5. {p5}\n\nWhich number (1-5) is the best? Reply with one digit only."),
])
pick_best_chain = pick_best_template | llm | StrOutputParser()


def pick_best_prompt_index(prompts: list[str], state: dict[str, Any]) -> int:
    """5 prompt arasından ürün bağlamına en uygun olanı seçer; 1-5 arası index döner."""
    if not prompts or len(prompts) < 5:
        return 1
    context = (state.get("items_story") or state.get("url_content") or state.get("user_prompt") or "")[:800]
    # Kısalt (LLM token tasarrufu)
    p1, p2, p3, p4, p5 = [p[:300] for p in prompts[:5]]
    out = pick_best_chain.invoke({"context": context, "p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5})
    out = (out or "").strip()
    for c in out:
        if c in "12345":
            return int(c)
    return 1
