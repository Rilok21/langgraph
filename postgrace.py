from typing import TypedDict, List
import psycopg2
import json
from langgraph.graph import StateGraph, END

# --------------------
# 1️⃣ Define Graph State
# --------------------
class State(TypedDict):
    messages: List[str]

# --------------------
# 2️⃣ Define Node
# --------------------
def chat_node(state: State):
    # Simulate LLM reply
    last_msg = state["messages"][-1]
    reply = f"Bot reply to: {last_msg}"
    return {"messages": state["messages"] + [reply]}




def ensure_table():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS langgraph_state (
            thread_id TEXT PRIMARY KEY,
            state JSONB
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

DB_PARAMS = {
    "dbname": "myapp",
    "user": "admin",
    "password": "password123",
    "host": "localhost",
    "port": 5432
}

ensure_table()

# --------------------
# 3️⃣ Setup Graph
# --------------------
graph = StateGraph(State)
graph.add_node("chat", chat_node)
graph.set_entry_point("chat")
graph.add_edge("chat", END)

app = graph.compile()  # ✅ no checkpointer here

# --------------------
# 4️⃣ PostgreSQL Helpers
# --------------------


def save_state(thread_id: str, state: dict):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS langgraph_state (
            thread_id TEXT PRIMARY KEY,
            state JSONB
        )
    """)
    cur.execute("""
        INSERT INTO langgraph_state(thread_id, state)
        VALUES (%s, %s)
        ON CONFLICT (thread_id) DO UPDATE SET state = EXCLUDED.state
    """, (thread_id, json.dumps(state)))
    conn.commit()
    cur.close()
    conn.close()

def load_state(thread_id: str) -> dict:
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        SELECT state FROM langgraph_state WHERE thread_id = %s
    """, (thread_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row[0]
    return {"messages": []}  # default empty state

# --------------------
# 5️⃣ Run Graph with Persistence
# --------------------
thread_id = "user_123"

# Load previous state
state = load_state(thread_id)

# Append user input
state["messages"].append("Hello LangGraph!")

# Invoke graph
new_state = app.invoke(state)

# Save updated state
save_state(thread_id, new_state)

# Print result
print("Updated messages:", new_state["messages"])
