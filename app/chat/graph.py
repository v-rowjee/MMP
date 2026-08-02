"""Chat LangGraph wiring."""

from langgraph.graph import END, START, StateGraph

from app.chat.nodes.workflow import (
    classify_question,
    compose_answer,
    execute_query,
    generate_sql,
    load_chat_context,
    persist_message,
    plan_data_query,
    retrieve_dashboard_context,
    validate_answer,
    validate_sql,
)
from app.chat.state import ChatState


class ChatWorkflow:
    def build(self):
        graph = StateGraph(ChatState)
        graph.add_node("load_chat_context", load_chat_context)
        graph.add_node("classify_question", classify_question)
        graph.add_node("retrieve_dashboard_context", retrieve_dashboard_context)
        graph.add_node("plan_data_query", plan_data_query)
        graph.add_node("generate_sql", generate_sql)
        graph.add_node("validate_sql", validate_sql)
        graph.add_node("execute_query", execute_query)
        graph.add_node("compose_answer", compose_answer)
        graph.add_node("validate_answer", validate_answer)
        graph.add_node("persist_message", persist_message)

        graph.add_edge(START, "load_chat_context")
        graph.add_edge("load_chat_context", "classify_question")
        graph.add_edge("classify_question", "retrieve_dashboard_context")
        graph.add_edge("classify_question", "plan_data_query")
        graph.add_edge("plan_data_query", "generate_sql")
        graph.add_edge("generate_sql", "validate_sql")
        graph.add_edge("validate_sql", "execute_query")
        graph.add_edge(["retrieve_dashboard_context", "execute_query"], "compose_answer")
        graph.add_edge("compose_answer", "validate_answer")
        graph.add_edge("validate_answer", "persist_message")
        graph.add_edge("persist_message", END)
        return graph.compile()


def build_chat_graph():
    return ChatWorkflow().build()
