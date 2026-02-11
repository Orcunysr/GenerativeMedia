"""Yüklenen fotoğrafları betimler; çıktı prompt üretiminde kullanılır (fotoğrafa göre prompt)."""
from typing import Any, Dict

from graph.chains.describe_image import describe_image_from_state
from graph.state import State


def describe_images_node(state: State) -> Dict[str, Any]:
    print("describe_images_node çalıştı")
    """
    State'teki yüklenen fotoğraf(lar)ı vision ile betimler.
    Sonuç state["image_description"] olarak saklanır; generate_image_prompt buna göre prompt yazar.
    """
    description = describe_image_from_state(state)
    return {"image_description": description}
