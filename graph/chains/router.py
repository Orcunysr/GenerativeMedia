"""Routes the user question to gather_information or create_advert."""
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from graph.config.llm import get_chat_model


class RouteQuery(BaseModel):
    """Which datasource to route the user question to."""

    datasource: Literal["gather_information", "create_advert"] = Field(
        ...,
        description="gather_information: collect or look up info. create_advert: create an advert.",
    )


system = """You are an ad assistant router. Use the user message and the current state to decide. Reply with exactly one word:
- If the user wants information, research, or is asking a question, or state is missing required info → gather_information
- If the user wants to create an advert and state has the needed info → create_advert
Your reply must be only: gather_information or create_advert. Do not add anything else."""

route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "State: {must_state}\n\nUser: {question}"),
    ]
)

chat = get_chat_model()


def _parse_route(msg) -> RouteQuery:
    """Parse gather_information or create_advert from the model reply."""
    text = getattr(msg, "content", msg) or ""
    t = str(text).strip().lower()
    if "create_advert" in t:
        return RouteQuery(datasource="create_advert")
    return RouteQuery(datasource="gather_information")


question_router = route_prompt | chat | _parse_route
