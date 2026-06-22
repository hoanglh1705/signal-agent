from langchain_openai import ChatOpenAI

from config import settings

def get_llm():
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openapi_api_key,
        temperature=0.1,
    )