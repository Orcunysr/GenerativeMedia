"""Wiro Sora 2 Pro ile poster + video_scenario'dan kısa reklam videosu üretir."""
from typing import Any, Dict

from graph.chains.create_video import create_video
from graph.state import State


def generate_video_node(state: State) -> Dict[str, Any]:
    print("generate_video_node çalıştı")
    """
    State'teki poster_image_address + video_scenario ile Wiro openai/sora-2-pro'dan video üretir.
    Hata olursa poster yine döner; video_image_address None kalır.
    """
    try:
        out = create_video(state)
        return {
            "video_image_address": out["video_image_address"],
            "generated_video_prompt": out.get("generated_video_prompt"),
            "generated": "İşte ürününüz için hazırladığım reklam posteri ve videosu! Temayı ve renkleri otomatik olarak ürün görselinden aldım. 🎨✨",
        }
    except Exception:
        return {
            "video_image_address": None,
            "generated_video_prompt": state.get("video_scenario"),
        }
