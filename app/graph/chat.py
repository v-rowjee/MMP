"""Chat LangGraph workflow skeleton."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class ChatState(TypedDict, total=False):
    analysis_id: str
    dataset_id: str
    session_id: str
    question: str
    history: list[dict[str, Any]]
    schema: dict[str, Any]
    dashboard_context: dict[str, Any]
    route: str
    query_plan: dict[str, Any] | None
    sql: str | None
    query_result: list[dict[str, Any]]
    answer: str
    errors: list[str]


class ChatWorkflow:
    def build(self):
        graph = StateGraph(ChatState)
        graph.add_node("load_chat_context", self.load_chat_context)
        graph.add_node("classify_question", self.classify_question)
        graph.add_node("retrieve_dashboard_context", self.retrieve_dashboard_context)
        graph.add_node("plan_data_query", self.plan_data_query)
        graph.add_node("generate_sql", self.generate_sql)
        graph.add_node("validate_sql", self.validate_sql)
        graph.add_node("execute_query", self.execute_query)
        graph.add_node("compose_answer", self.compose_answer)
        graph.add_node("validate_answer", self.validate_answer)
        graph.add_node("persist_message", self.persist_message)

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

    def load_chat_context(self, state: ChatState) -> dict[str, Any]:
        return {
            "history": state.get("history", []),
            "schema": state.get("schema", {}),
        }

    def classify_question(self, state: ChatState) -> dict[str, Any]:
        return {"route": state.get("route", "dashboard")}

    def retrieve_dashboard_context(self, state: ChatState) -> dict[str, Any]:
        return {"dashboard_context": state.get("dashboard_context", {})}

    def plan_data_query(self, state: ChatState) -> dict[str, Any]:
        return {"query_plan": state.get("query_plan")}

    def generate_sql(self, state: ChatState) -> dict[str, Any]:
        return {"sql": state.get("sql")}

    def validate_sql(self, state: ChatState) -> dict[str, Any]:
        return {"errors": state.get("errors", [])}

    def execute_query(self, state: ChatState) -> dict[str, Any]:
        return {"query_result": state.get("query_result", [])}

    def compose_answer(self, state: ChatState) -> dict[str, Any]:
        return {"answer": state.get("answer", "")}

    def validate_answer(self, state: ChatState) -> dict[str, Any]:
        return {"errors": state.get("errors", [])}

    def persist_message(self, state: ChatState) -> dict[str, Any]:
        return {}


def build_chat_graph():
    return ChatWorkflow().build()
