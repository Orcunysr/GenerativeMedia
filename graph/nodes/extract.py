from typing import Any, Dict

from graph.chains.state_extraction import extract_state_for_update
from graph.state import State

# Kullanıcı "sen seç/sen belirle/yok/farketmez" dediğinde tercih sistemde kalsın → poster ve video ikisi de
NO_PREFERENCE_KEYWORDS = (
    "sen belirle", "sen seç", "sen karar ver", "yok", "farketmez", "fark etmez",
    "genel olarak yok", "genel yok", "ikisi de", "her ikisi", "ikisini de", "belirlemen", "sana bırak",
)


def _parse_prompt_choice(question: str, prompt_options: list) -> int | None:
    """Kullanıcı 1-5 seçtiyse index (0-4) döner."""
    q = question.strip().lower()
    if q in ("1", "2", "3", "4", "5"):
        return int(q) - 1
    if q in ("birinci", "1 numara", "1. seç", "1 numarayı"):
        return 0
    if q in ("ikinci", "2 numara", "2. seç", "2 numarayı"):
        return 1
    if q in ("üçüncü", "3 numara", "3. seç", "3 numarayı"):
        return 2
    if q in ("dördüncü", "4 numara", "4. seç", "4 numarayı"):
        return 3
    if q in ("beşinci", "5 numara", "5. seç", "5 numarayı"):
        return 4
    return None


def extract_node(state: State) -> Dict[str, Any]:
    """Kullanıcı mesajından (ve varsa url_content) state alanlarını çıkarır (state_extraction)."""
    question = (state.get("question") or "").strip()
    prompt_options = state.get("prompt_options") or []
    idx = _parse_prompt_choice(question, prompt_options)
    if idx is not None and 0 <= idx < len(prompt_options):
        return {
            "question": "Poster ve video oluştur",
            "user_selected_prompt": prompt_options[idx],
            "selected_prompt_index": idx + 1,
        }
    context = state.get("url_content") or ""
    updates = extract_state_for_update(user_message=question, context=context)
    out = dict(updates)
    # Kullanıcının verdiği URL'yi extract ile ezme (LLM bazen mesajdaki başka linki çıkarıyor)
    existing_url = (state.get("url") or "").strip()
    if existing_url and existing_url.startswith("http") and "url" in out:
        out.pop("url", None)
    # "Sen belirle / yok / farketmez" → user_prompt'u "poster ve video" yap; ikisini de üretelim
    if any(k in question.lower() for k in NO_PREFERENCE_KEYWORDS):
        out["user_prompt"] = "poster ve video"
    if not out:
        out = {"question": question}
    return out
