from typing import Any, Dict

from graph.chains.create_foto import create_foto
from graph.state import State


def generate_image_node(state: State) -> Dict[str, Any]:
    print("generate_image_node çalıştı")
    """Generates the actual image using the prompt from state."""
    prompt = state.get("generated_image_prompt") or ""
    
    # If no prompt generated, fallback or error message?
    # Ideally prompt should be there from previous node.
    if not prompt:
        return {"generated": "Görsel promptu oluşturulamadı."}

    try:
        # We pass prompt explicitly so create_foto doesn't try to regenerate it
        out = create_foto(state, prompt=prompt)
        
        url = out.get("poster_image_address") or ""
        prompt_used = out.get("generated_image_prompt") or prompt
        ref_images = out.get("input_image_urls") or []
        
        msg = f"Görsel oluşturuldu.\n\n{url}"
        if prompt_used:
            msg += f"\n\n[Wiro'ya giden prompt]\n{prompt_used}"
        if ref_images:
            msg += f"\n\n[Referans görsel]\n{ref_images[0]}"
            
        return {
            "poster_image_address": url,
            "generated": msg if url else "Görsel üretildi ancak URL alınamadı.",
        }
    except Exception as e:
        return {"generated": f"Görsel oluşturulurken hata: {e}"}
