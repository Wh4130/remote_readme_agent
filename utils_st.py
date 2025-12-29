import streamlit as st
import pandas as pd
import time
import datetime as dt
import json

def stream_data(msg):
    for word in msg.split(" "):
        yield word + " "
        time.sleep(0.02)

def format_message(message):
    if not (message.startswith("{") and message.endswith("}")):
        return message
    
    body = json.loads(message)
    if "message" in body:
        return body['message']
    elif "result" in body:
        return body['result']
    else:
        return 

def format_tool_calls(messages):
    if not messages:
        return 
    value = ""
    for message in messages:
        tool_name = message.function.name
        tool_args = message.function.arguments
        value += "> " + tool_name + ": " + tool_args + "\n"
    return value


def add_global_memory(agent_name, memory):
    if "global_memory" not in st.session_state:
        st.session_state["global_memory"] = []
        
    
    st.session_state['global_memory'].append(
        {"agent_session": agent_name, 
            "role": memory.get("role", None),
            "content": memory.get("content", None),
            "tool_calls": memory.get("tool_calls", None),
            "time": memory.get("time", None)
        }
    )


@st.dialog("Global Memory", width = "large")
def render_global_memory():
    df = pd.DataFrame(st.session_state['global_memory'])
    df['time'] = df['time'].apply(lambda x: dt.datetime.fromtimestamp(float(x)).strftime("%Y-%m-%d %H:%M:%S"))

    LEFT, RIGHT = st.columns((0.2, 0.8))
    with LEFT:
        agent = st.selectbox("Agent filter", ['all'] + df['agent_session'].unique().tolist(), index = 0)
        mode  = st.pills("Render mode", ["raw", "concise"], default = "concise")

    with RIGHT:
        if agent != "all":
            df = df[df['agent_session'] == agent]

        if mode == "concise":
            df['content'] = df['content'].apply(lambda x: format_message(x))
            df['tool_calls'] = df['tool_calls'].apply(lambda x: format_tool_calls(x))

        st.dataframe(df.sort_values(by = "time", ascending = True))