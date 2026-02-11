from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict, total=False):
    """
        State of the conversation.
        messages: ReAct/ToolNode için; agent ve tool çıktıları (add_messages ile birleşir).
    Args:
        # General
        generated: Generated answer
        question: Question asked by the user
        activity: Activity of the user

        # Tools
        tavily_search_results: Results of the tavily search
        url: URL of the url
        url_content: Content of the url

        # Items
        items_quality: Quality of the items
        items_story: Story of the items
        items_image_address: Address of the items image

        # User
        user_prompt: Prompt of the user
        user_image_address: Kullanıcı fotoğrafı — yerel dosya yolu (bilgisayardan upload) veya http(s) URL

        # Poster
        poster_promt: Prompt of the poster
        poster_image_address: Address of the poster image
        prompt_options: URL'den üretilen 5 farklı poster promptu; kullanıcı 1-5 seçer
        user_selected_prompt: Kullanıcının seçtiği prompt metni

        # Görsel açıklaması (yüklenen fotoğraflardan vision ile üretilir; prompt buna göre yazılır)
        image_description: Optional[str]

        # Video
        video_promt: Prompt of the video
        video_image_address: Address of the video image
        video_scenario: Reklam filmi senaryosu (image_to_movie_prompt ile üretilen)
        generated_video_prompt: Videoya gönderilen prompt (create_video)
        conversation_history: Sohbet geçmişi (["User: ...", "Assistant: ..."]); bağlam için.
    """
    messages: Annotated[list, add_messages]
    conversation_history: Optional[list[str]]
    generated: Optional[str]
    question: Optional[str]
 
    activity : Optional[Literal["gather_information", "create_advert"]]

    tavily_search_results: Optional[list[str]]
    url_content: Optional[str]
    url : Optional[str]

    # User prompt
    user_prompt: Optional[str]
    user_image_address: Optional[str]

    items_quality : Optional[int]
    items_story: Optional[str]
    items_image_address: Optional[str]

    poster_promt: Optional[str]
    poster_image_address: Optional[str]
    generated_image_prompt: Optional[str]
    prompt_options: Optional[list[str]]
    selected_prompt_index: Optional[int]
    user_selected_prompt: Optional[str]
    image_description: Optional[str]

    video_promt: Optional[str]
    video_image_address: Optional[str]
    video_scenario: Optional[str]
    generated_video_prompt: Optional[str]


