from graph.state import State

def state_to_str(state: State) -> str:
    """State'i router/generation prompt'a vermek için kısa string. messages atlanır."""
    parts = []
    for k, v in state.items():
        if k in ("messages", "conversation_history") or v is None or v == "":
            continue
        parts.append(f"{k}: {v!r}"[:80])
    return "\n".join(parts) if parts else "(empty)"
