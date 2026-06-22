from langgraph.graph import StateGraph, END

from nodes.generate_signal import generate_signal
from nodes.validate_signal import validate_signal
from nodes.build_context import build_context
from nodes.load_news import load_news
from nodes.load_price import load_price
from state import SignalState

LOAD_PRICE = "load_price"
LOAD_NEWS = "load_news"
BUILD_CONTEXT = "build_context"
GENERATE_SIGNAL = "generate_signal"
VALIDATE_SIGNAL = "validate_signal"


def build_signal_graph():
    graph = StateGraph(SignalState)

    graph.add_node(LOAD_PRICE, load_price)
    graph.add_node(LOAD_NEWS, load_news)
    graph.add_node(BUILD_CONTEXT, build_context)
    graph.add_node(GENERATE_SIGNAL, generate_signal)
    graph.add_node(VALIDATE_SIGNAL, validate_signal)

    graph.set_entry_point(LOAD_PRICE)

    graph.add_edge(LOAD_PRICE, LOAD_NEWS)
    graph.add_edge(LOAD_NEWS, BUILD_CONTEXT)
    graph.add_edge(BUILD_CONTEXT, GENERATE_SIGNAL)
    graph.add_edge(GENERATE_SIGNAL, VALIDATE_SIGNAL)
    graph.add_edge(VALIDATE_SIGNAL, END)

    return graph.compile()

signal_graph = build_signal_graph()

async def run_signal_graph(request):
    state = await signal_graph.ainvoke({"request": request})
    signal = state["signal"]

    signal["metadata"] = {
        "validation_errors": state.get("validation_errors", []),
        "news_count": len(state.get("news_items", [])),
        "has_price_history": bool(state.get("has_price_history")),
    }

    return signal

