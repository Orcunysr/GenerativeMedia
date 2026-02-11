"""LangGraph: ReAct tarzı tool node ile bilgi toplama; poster/video Wiro ile."""
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from graph.state import State
from graph.tools import tools
from graph.nodes.router import router_node
from graph.nodes.extract import extract_node
from graph.nodes.gather_agent import gather_agent_node
from graph.nodes.gather_finish import gather_finish_node
from graph.nodes.describe_images import describe_images_node
from graph.nodes.generate_image_prompt import generate_image_prompt_node
from graph.nodes.generate_image import generate_image_node
from graph.nodes.generate_video_scenario import generate_video_scenario_node
from graph.nodes.generate_video import generate_video_node


def _route_after_router(state: State) -> str:
    """Router sonrası: gather_information → extract; create_advert → describe_images."""
    activity = state.get("activity") or "gather_information"
    return "extract" if activity == "gather_information" else "describe_images"


def _after_gather_agent(state: State) -> str:
    """Son mesajda tool_calls varsa tools node'a, yoksa gather_finish'e."""
    messages = state.get("messages") or []
    if not messages:
        return "gather_finish"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "gather_finish"


builder = StateGraph(State)

# Nodes
builder.add_node("router", router_node)
builder.add_node("extract", extract_node)
builder.add_node("gather_agent", gather_agent_node)
builder.add_node("tools", ToolNode(tools))
builder.add_node("gather_finish", gather_finish_node)
builder.add_node("describe_images", describe_images_node)
builder.add_node("generate_image_prompt", generate_image_prompt_node)
builder.add_node("generate_image", generate_image_node)
builder.add_node("generate_video_scenario", generate_video_scenario_node)
builder.add_node("generate_video", generate_video_node)

# Edges
builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    _route_after_router,
    {"extract": "extract", "describe_images": "describe_images"},
)
builder.add_edge("extract", "gather_agent")
def _route_after_gather_finish(state: State) -> str:
    """If gather_finish decided to create explicitly (auto mode), go to describe_images."""
    if state.get("activity") == "create_advert":
        return "describe_images"
    return END


builder.add_conditional_edges("gather_agent", _after_gather_agent, {"tools": "tools", "gather_finish": "gather_finish"})
builder.add_edge("tools", "gather_agent")
builder.add_conditional_edges("gather_finish", _route_after_gather_finish, {"describe_images": "describe_images", END: END})

# create_advert: fotoğraflar → betimleme → prompt → görsel → reklam filmi senaryosu
builder.add_edge("describe_images", "generate_image_prompt")
builder.add_edge("generate_image_prompt", "generate_image")
builder.add_edge("generate_image", "generate_video_scenario")
builder.add_edge("generate_video_scenario", "generate_video")
builder.add_edge("generate_video", END)


graph = builder.compile()

try:
    graph.get_graph().draw_mermaid_png(output_file_path="workflow.png")
except Exception:
    # Optional: Skip drawing if dependencies missing
    pass
