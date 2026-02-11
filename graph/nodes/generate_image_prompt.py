from typing import Any, Dict

from graph.chains.create_image_prompt import create_image_prompt
from graph.state import State


def generate_image_prompt_node(state: State) -> Dict[str, Any]:
    print("generate_image_prompt_node çalıştı")
    """State'ten (items_story, items_image_address vb.) görsel promptu oluşturur."""
    # Eğer router veya bir önceki adımda prompt seçilmiş/hazırlanmışsa onu kullan
    if state.get("generated_image_prompt"):
        return {"generated_image_prompt": state["generated_image_prompt"]}

    generated_prompt = create_image_prompt(state)
    return {"generated_image_prompt": generated_prompt}
