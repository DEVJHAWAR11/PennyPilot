from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    message: str

def dummy_node(state: State):
    return {"message": state["message"] + " World!"}

graph = StateGraph(State)
graph.add_node("dummy", dummy_node)
graph.add_edge(START, "dummy")
graph.add_edge("dummy", END)

app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({"message": "Hello"})
    print("LangGraph result:", result)
