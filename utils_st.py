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
    if not isinstance(messages, list):
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
    if not st.session_state['global_memory']:
        st.warning("No memory yet!")
    else:
        df = pd.DataFrame(st.session_state['global_memory'])
        df['time_on_display'] = df['time'].apply(lambda x: dt.datetime.fromtimestamp(float(x)).strftime("%Y-%m-%d %H:%M:%S"))

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

            st.dataframe(df.sort_values(by = "time", ascending = True),
                column_config = {
                    "time": None
                }
            )

def render_sidebar(agent_registry):
    """
    Render a streamlit sidebar
    
    :param agent_registry: the AgentRegistry object
    """
    with st.sidebar:
        st.header("README Writer Agent")
        st.caption("A multi-agent system that analyzes a remote git repository and writes a README.md file. Start using it by pasting a :blue[**public remote github repository url.**]")
        st.logo("assets/icon.png", size = 'large')

        st.subheader(":material/output_circle: **Most Recent Result**")
        with st.container(border = True):
            if "README" in st.session_state:
                st.download_button(
                    label = "README.md",
                    data = st.session_state.README,
                    file_name = "README.md",
                    icon = ":material/download:",
                    width = "stretch",
                    key = f"{time.time()}",
                    disabled = st.session_state['running']
                )
            else:
                st.warning("No result yet.")

        st.subheader(":material/support_agent: **Sub-agent List**",
                         help = "expand the toggle list to see tools available to each agent.")
        with st.container(border = True, height = 120):
            for agent in agent_registry.agents.keys():
                with st.expander(agent):
                    text = "\n"
                    for tool in agent_registry.get_agent_tool_registry(agent):
                        text += f"> {tool}\n"
                    st.write(f"```{text}```")


        st.subheader(":material/memory: **Analyze Global Memory**")
        with st.container(border = True):
            st.caption(":red[Clicking this button will interrupt any running session.]")
            if st.button("Click to open", width = "stretch", disabled = st.session_state['running']):
                render_global_memory()

            "Other sidebar design components go here"
        
def handle_running_session(func):
    def wrapper():
        if "running" not in st.session_state:
            st.session_state['running'] = True 
        st.session_state['running'] = True
        func()
        st.session_state['running'] = False 
    return wrapper

def set_session_running():
    if "running" not in st.session_state:
        st.session_state['running'] = True 
    st.session_state['running'] = True