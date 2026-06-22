from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from config import settings


def get_llm():
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openapi_api_key,
        temperature=0.1,
    )


def get_groq_llm(temperature: float = 0.0):
    """LLM Groq dùng cho chấm điểm bài tin. Trả JSON nên temperature thấp."""
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
    )
