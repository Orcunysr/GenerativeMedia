"""Üretilen reklam görseli bağlamından reklam filmi senaryosu yazar (image_to_movie_prompt)."""
from typing import Any, Dict

from graph.chains.image_to_movie_prompt import create_video_scenario
from graph.state import State


def generate_video_scenario_node(state: State) -> Dict[str, Any]:
    print("generate_video_scenario_node çalıştı")
    """
    State'teki ürün + üretilmiş poster/görsel bilgisinden kısa reklam filmi senaryosu üretir.
    Sonuç state["video_scenario"] olarak döner.
    """
    scenario = create_video_scenario(state)
    return {"video_scenario": scenario}
