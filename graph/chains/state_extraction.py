"""
Chain that extracts state fields from the user message.
Use this to fill State from what the user wrote (e.g. URL, what they want, story, quality).
"""
import json
import re
from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from graph.config.llm import get_chat_model

# Fields we can extract from user text (not file paths from messages).
# user_image_address metinden çıkarılmaz; kullanıcı bilgisayardan dosya yüklediğinde
# çağıran taraf state["user_image_address"] = yüklenen dosyanın yolu olarak set etmeli.
EXTRACTABLE_KEYS = {
    "user_prompt",
    "url",
    "items_story",
    "items_quality",
    "poster_promt",
    "video_promt",
}


class ExtractedState(BaseModel):
    """Fields that can be extracted from a user message."""

    user_prompt: Optional[str] = Field(default=None, description="What the user wants (e.g. poster, ad, video)")
    url: Optional[str] = Field(default=None, description="URL if the user shared a link")
    items_story: Optional[str] = Field(default=None, description="Product/story description the user gave")
    items_quality: Optional[int] = Field(default=None, description="Quality level if mentioned (e.g. 1-10)")
    poster_promt: Optional[str] = Field(default=None, description="Poster idea or prompt if mentioned")
    video_promt: Optional[str] = Field(default=None, description="Video idea or prompt if mentioned")


system_prompt = """You extract structured information from the user message for an ad assistant.

From the user message (and optional context), extract only the fields that are clearly present. Ignore fields you cannot infer.

Output format: valid JSON only, no other text. Use exactly these keys when present: user_prompt, url, items_story, items_quality, poster_promt, video_promt.
- user_prompt: what the user wants (e.g. "poster", "video") OR a theme/style they ask for (e.g. "kumsal teması", "minimalist stil", "doğal ortam")
- url: any URL or link the user shared
- items_story: description of product/story they gave
- items_quality: number if they mentioned quality (e.g. 8)
- poster_promt / video_promt: specific idea or theme for poster/video (e.g. "kumsal", "minimalist", "banyo dekoru")

Example: {{"user_prompt": "kumsal teması"}} or {{"poster_promt": "minimalist stil"}}
Only include keys you found. Reply with nothing but the JSON object."""

extraction_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "Context (optional): {context}\n\nUser message: {user_message}"),
])

chat = get_chat_model()


def _parse_json_from_text(text: str) -> dict[str, Any]:
    """Extract a JSON object from model output (may be wrapped in markdown or extra text)."""
    text = (text or "").strip()
    # Try to find {...}
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _to_state_update(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep only keys that exist in State and have a value."""
    return {k: v for k, v in raw.items() if k in EXTRACTABLE_KEYS and v is not None and v != ""}


def parse_extraction(msg) -> dict[str, Any]:
    """Parse LLM output to a state update dict."""
    text = getattr(msg, "content", msg) or ""
    raw = _parse_json_from_text(str(text))
    return _to_state_update(raw)


# Chain: user_message (+ optional context) -> LLM -> JSON text -> state update dict
extraction_chain = (
    extraction_prompt
    | chat
    | StrOutputParser()
)

# Full chain including parse to dict (invoke returns string; use extract_state_for_update for dict)
def extract_state_for_update(user_message: str, context: str = "") -> dict[str, Any]:
    """
    Run extraction and return a dict suitable for updating State.
    Only includes keys that were extracted; merge with existing state in the graph.
    """
    result = extraction_chain.invoke({
        "user_message": user_message,
        "context": context or "(none)",
    })
    raw = _parse_json_from_text(str(result))
    return _to_state_update(raw)
