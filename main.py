"""
Etkileşimli mod: Döngüde kullanıcı ile konuşarak poster/video üretimi veya bilgi toplama.
Çıkmak için: çık, quit, exit, q
"""
import os
import sys

# Patch / path (user_scenario_test ile aynı)
try:
    import langchain_core.pydantic_v1
except ImportError:
    try:
        from pydantic import v1 as pydantic_v1
        sys.modules["langchain_core.pydantic_v1"] = pydantic_v1
    except ImportError:
        pass
sys.path.insert(0, os.getcwd())

from graph.graph import graph
from graph.state import State


# State'te toplanan veriyi gösteren alanlar (kısa özet)
STATE_COLLECTED_KEYS = (
    "url",
    "url_content",
    "tavily_search_results",
    "items_story",
    "items_image_address",
    "user_image_address",
    "user_prompt",
    "poster_promt",
    "video_promt",
    "items_quality",
)


def _print_state_collected(result: State) -> None:
    """Sistemin topladığı veriyi (state) kısa özet olarak gösterir."""
    lines: list[str] = []
    for key in STATE_COLLECTED_KEYS:
        v = result.get(key)
        if v is None or v == "":
            continue
        if key == "url":
            lines.append(f"  url: {v[:80]}{'...' if len(str(v)) > 80 else ''}")
        elif key == "url_content":
            s = (v[:120] + "...") if len(str(v)) > 120 else str(v)
            lines.append(f"  url_content: {s}")
        elif key == "tavily_search_results":
            arr = v if isinstance(v, list) else [v]
            lines.append(f"  tavily: {len(arr)} sonuç")
        elif key == "items_story":
            s = (v[:100] + "...") if len(str(v)) > 100 else str(v)
            lines.append(f"  items_story: {s}")
        elif key == "items_image_address":
            lines.append(f"  items_image_address: {v[:70]}{'...' if len(str(v)) > 70 else ''}")
        elif key == "user_image_address":
            lines.append(f"  user_image_address: {v}")
        else:
            lines.append(f"  {key}: {v}")
    if lines:
        print("\n--- Toplanan veri (state) ---")
        print("\n".join(lines))


def _print_result(result: State) -> None:
    """Graf çıktısını özetler; önce toplanan state, sonra cevap."""
    _print_state_collected(result)
    if result.get("generated"):
        print("\n--- Cevap ---\n", result["generated"])
    if result.get("image_description"):
        print("\n[Görsel betimi]", result["image_description"])
    if result.get("generated_image_prompt"):
        print("\n[Görsel prompt]", result["generated_image_prompt"])
    if result.get("poster_image_address"):
        print("\n[Poster URL]", result["poster_image_address"])
    if result.get("video_scenario"):
        print("\n--- Reklam filmi senaryosu ---\n", result["video_scenario"])
    if result.get("video_image_address"):
        print("\n[Video URL]", result["video_image_address"])
    elif result.get("video_scenario"):
        print("\n[Video] Şu an hazırlanamadı; poster kullanılabilir.")


def _parse_turn(line: str, state: State) -> State:
    """
    Kullanıcı satırını ayrıştırıp state günceller.
    - 'foto: /yol' veya 'resim: /yol' → user_image_address
    - 'url: https://...' veya 'ürün: https://...' → url
    - 'ürün hikaye: ...' → items_story
    - Sadece dosya yolu (var olan dosya) → user_image_address, question = "Poster oluştur"
    - Diğer → question
    """
    line = line.strip()
    if not line:
        return state

    updates: dict = {}

    lower = line.lower()
    if lower.startswith("foto:") or lower.startswith("resim:"):
        path = line.split(":", 1)[1].strip().strip('"\'')
        if os.path.isfile(path):
            updates["user_image_address"] = path
            updates["question"] = "Poster ve reklam videosu oluştur."
        else:
            print(f"[Uyarı] Dosya bulunamadı: {path}")
        return {**state, **updates} if updates else state

    if lower.startswith("url:") or lower.startswith("ürün:"):
        url = line.split(":", 1)[1].strip().strip('"\'')
        if url.startswith("http://") or url.startswith("https://"):
            updates["url"] = url
            updates["question"] = state.get("question") or "Ürün bilgisi topla."
        return {**state, **updates} if updates else state

    if lower.startswith("ürün hikaye:") or lower.startswith("items_story:"):
        story = line.split(":", 1)[1].strip().strip('"\'')
        updates["items_story"] = story
        return {**state, **updates} if updates else state

    # Tek başına URL (sistem sayfayı çekip bilgi toplayacak)
    if line.startswith("http://") or line.startswith("https://"):
        updates["url"] = line
        updates["question"] = "Bu ürün linki için bilgi topla; poster veya video istiyorum."
        return {**state, **updates}

    # Tek başına dosya yolu
    if os.path.isfile(line):
        updates["user_image_address"] = line
        updates["question"] = "Poster ve reklam videosu oluştur."
        return {**state, **updates}

    updates["question"] = line
    return {**state, **updates}


def run_interactive() -> None:
    state: State = {}
    print("GenerativeMedia — Etkileşimli mod. Çıkmak için: çık, quit, exit, q\n")
    print("Örnek: 'Poster oluştur', 'foto: /yol/resim.jpg', 'url: https://...', 'ürün hikaye: ...'\n")

    while True:
        try:
            line = input("Siz: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nÇıkılıyor.")
            break

        if not line:
            continue
        if line.lower() in ("çık", "quit", "exit", "q"):
            print("Çıkılıyor.")
            break

        state = _parse_turn(line, state)
        if not state.get("question") and not state.get("user_image_address"):
            continue

        print("İşleniyor...")
        try:
            result = graph.invoke(state)
            # Geçmişe bu turu ekle (sonraki turda bağlam için)
            history = list(state.get("conversation_history") or [])
            history.append(f"User: {line}")
            history.append(f"Assistant: {result.get('generated') or ''}")
            state = {**result, "conversation_history": history}
            _print_result(result)
        except Exception as e:
            print(f"Hata: {e}")
            import traceback
            traceback.print_exc()
        print()


def main():
    run_interactive()


if __name__ == "__main__":
    main()
