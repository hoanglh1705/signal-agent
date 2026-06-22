import json

from langchain_core.messages import  HumanMessage,SystemMessage

from llm import get_llm
from prompts import SIGNAL_SYSTEM_PROMPT
from state import SignalState


def _extract_text(content) -> str:
    """Normalize LLM content to a string.

    Some providers/models return content as a list of content blocks
    (e.g. [{"type": "text", "text": "..."}]) instead of a plain string.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
            else:
                parts.append(getattr(block, "text", ""))
        return "".join(parts)

    return str(content)


async def generate_signal(state: SignalState) -> SignalState:
    llm = get_llm()
    context = state["signal_context"]

    messages = [
        SystemMessage(content=SIGNAL_SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(context, ensure_ascii=False)),
    ]

    response = llm.invoke(messages)
    raw = _extract_text(response.content)

    try:
        signal = json.loads(raw)
    except Exception as e:
        print(e)
        signal = {}



    return {
        **state,
        "signal": signal,
    }
