from typing import Any, Dict

from graph.chains.router import question_router
from graph.state import State
from graph.utils import state_to_str


def _should_route_to_create(state: State) -> bool:
    print("router_node çalıştı")
    """Create mode'a geç: prompt seçildiyse, auto (farketmez) denildiyse veya foto/ürün + hazırla/yap denildiyse."""
    question = (state.get("question") or "").lower().strip()
    
    # 1. Prompt zaten seçili mi?
    if state.get("generated_image_prompt"):
        return True
    
    has_image = bool((state.get("items_image_address") or "").strip()) or bool((state.get("user_image_address") or "").strip())
    if not has_image:
        return False

    # 2. Auto-mode (farketmez, sen seç, vb.)
    AUTO_KEYWORDS = ("sende", "kafana göre", "sen seç", "farketmez", "sen karar ver", "top sende", "devam et")
    wants_auto = any(k in question for k in AUTO_KEYWORDS)
    if wants_auto:
        return True

    # 3. Açık üretim isteği (hazırla, yap, oluştur) — sadece fotoğraf yüklüyse bile create_advert'e geç
    WANTS_CREATE = ("hazırla", "yap", "oluştur", "başla", "reklam yap", "poster", "video", "oluştur")
    wants_create = any(k in question for k in WANTS_CREATE)
    return wants_create


def router_node(state: State) -> Dict[str, Any]:
    """Kullanıcı sorusu + state'e göre gather_information veya create_advert seçer."""
    question = (state.get("question") or "").strip()
    
    # 1. Prompt seçimi (1-5) varsa direkt üretime geç
    if state.get("prompt_options") and question.isdigit():
        choice = int(question)
        if 1 <= choice <= len(state["prompt_options"]):
            selected_prompt = state["prompt_options"][choice - 1]
            return {
                "activity": "create_advert",
                "generated_image_prompt": selected_prompt,
                "question": f"Seçilen prompt: {selected_prompt[:50]}..." # Log purpose
            }

    if _should_route_to_create(state):
        return {"activity": "create_advert"}
    
    route = question_router.invoke({
        "question": question,
        "must_state": state_to_str(state),
    })
    
    activity = route.datasource
    # Override: Don't create unless we are ready (prompt selected or auto)
    if activity == "create_advert" and not _should_route_to_create(state):
        activity = "gather_information"
        
    return {"activity": activity}
