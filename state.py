from typing import Any, TypedDict

from schemas import SignalRequest


class SignalState(TypedDict, total=False):
    request: SignalRequest

    price_history: list[dict[str, Any]]
    news_items: list[dict[str, Any]]
    macro_context: dict[str, Any]
    geopolitical_context: dict[str, Any]

    signal_context: dict[str, Any]
    raw_llm_response: str
    signal: dict[str, Any]

    validation_errors: list[str]
    metadata: dict[str, Any]