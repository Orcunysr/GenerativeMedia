"""Tool çağrıları bittikten sonra mesajlardan state alanlarını doldurur ve kullanıcı cevabı üretir."""
from typing import Any, Dict

from langchain_core.messages import ToolMessage

from graph.chains.create_image_prompt import create_5_prompt_options, pick_best_prompt_index
from graph.chains.gather_info_gen import generation_chain
from graph.state import State
from graph.utils import state_to_str

WANTS_CREATE_KEYWORDS = ("hazırla", "yap", "oluştur", "başla", "reklam yap", "poster", "video", "hazırlıyorum", "oluştur")


def _tool_name_to_state_key(name: str) -> str | None:
    if name == "fetch_url":
        return "url_content"
    if name == "get_main_image_url_tool":
        return "items_image_address"
    if name == "tavily_search":
        return "tavily_search_results"
    return None


def gather_finish_node(state: State) -> Dict[str, Any]:
    print("gather_finish_node çalıştı")
    """messages içindeki ToolMessage sonuçlarını state'e yazar; generation_chain ile 'generated' üretir."""
    messages = state.get("messages") or []
    updates: Dict[str, Any] = {}
    for msg in messages:
        if isinstance(msg, ToolMessage):
            key = _tool_name_to_state_key(msg.name)
            if key:
                content = (msg.content or "").strip()
                if key == "tavily_search_results":
                    updates[key] = [content] if content else []
                else:
                    updates[key] = content
    merged = {**state, **updates}
    if state.get("url"):
        merged.setdefault("url", state["url"])
    question = (merged.get("question") or "").lower().strip()
    has_product_info = bool(merged.get("url") and (merged.get("items_story") or merged.get("url_content") or merged.get("items_image_address")))
    wants_create = any(k in question for k in WANTS_CREATE_KEYWORDS)

    
    # Auto-create keywords (user gives control)
    AUTO_KEYWORDS = ("sende", "kafana göre", "sen seç", "farketmez", "sen karar ver", "top sende", "devam et")
    wants_auto = any(k in question for k in AUTO_KEYWORDS)

    # Detect if user just sent a URL (Turn 1) vs Text (Turn 2)
    is_url_input = question.startswith("http://") or question.startswith("https://") or "url:" in question

    if has_product_info:
        # A. Auto Mode -> Direkt üretim
        if wants_auto and merged.get("items_image_address"):
            updates["activity"] = "create_advert"
            updates["generated"] = "Ürün bilgilerini aldım, analiz edip hemen üretime geçiyorum! 🎨"
            return updates

        # B. Prompt Options Generation (Turn 2 OR Explicit Request)
        # Generate options if:
        # 1. User sent text (not just URL) implies refinement or confirmation
        # 2. User explicitly used creation keywords ("yap", "hazırla")
        # 3. We already asked and user replied (inferred via text input)
        if (not is_url_input) or wants_create:
            if not merged.get("prompt_options"):
                try:
                    five = create_5_prompt_options(merged)
                    if five:
                        updates["prompt_options"] = five
                        best_idx = pick_best_prompt_index(five, merged)
                        updates["user_selected_prompt"] = five[best_idx - 1]
                        updates["selected_prompt_index"] = best_idx
                        updates["activity"] = "create_advert"
                        lines = [
                            f"Ürün bilgisine göre 5 farklı poster prompt'u hazırladım. En uygun gördüğüm {best_idx}. seçenek — bu seçenekle poster ve video oluşturuyorum.",
                            "(İsterseniz 1–5 yazarak farklı bir seçenek belirtebilirsiniz.)\n",
                        ]
                        for i, p in enumerate(five, 1):
                            lines.append(f"{i}. {p[:120]}{'...' if len(p) > 120 else ''}")
                        updates["generated"] = "\n".join(lines)
                        return updates
                except Exception:
                    pass

        # C. Just Gathered (Turn 1) -> Ask for additions
        # If we just got the URL and user didn't say "make it" or "auto", ask:
        if is_url_input and not wants_create:
            summary = (merged.get("items_story") or merged.get("url_content") or "")[:200]
            summary_text = f"📝 Ürün: {summary}...\n\n" if summary else ""
            updates["generated"] = f"Ürün bilgilerini başarıyla topladım! 🛍️\n{summary_text}Reklam kampanyası için eklemek istediğiniz özel bir tema veya detay var mı? (Örn: 'Kumsal teması', 'Minimalist', 'yok devam et')"
            return updates

    all_state_str = state_to_str(merged)
    # ... rest of generation chain fallback ...

    all_state_str = state_to_str(merged)
    history = state.get("conversation_history") or []
    conversation_history_str = "\n".join(history) if history else "(yok)"
    generated = generation_chain.invoke({
        "all_state": all_state_str,
        "question": merged.get("question") or "",
        "conversation_history": conversation_history_str,
    })
    updates["generated"] = generated
    return updates
