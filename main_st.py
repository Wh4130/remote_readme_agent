# Import manager agent from agents folder
from agents.manager import manager_agent

# TODO Import sub-agents from agents folder
from agents.writer_agent import writer_agent
from agents.web_search_agent import web_search_agent
from agents.db_manager_agent import google_sheet_agent

# Import necessary components
from components.game import ActionContext, Goal, Action, ActionRegistry, Memory
from components.frame import AgentRegistry, Agent

# Import utilities
from utils_st import stream_data, render_sidebar, handle_running_session, set_session_running


# Configuration
# variables with all capital letters are constants in the config file 
from config import *

import streamlit as st
import time, json
from dotenv import dotenv_values


if "global_memory" not in st.session_state:
    st.session_state["global_memory"] = []
if "running" not in st.session_state:
    st.session_state['running'] = False

# TODO 1. Construct Agent Registry and register all sub-agents
registry = AgentRegistry()
# registry.register_agent(writer_agent.name, writer_agent.run)
registry.register_agent(web_search_agent.name, web_search_agent)
registry.register_agent(google_sheet_agent.name, google_sheet_agent)

# 2. Construct ActionContext instance
# Note: This is where the Registry is actually passed in
action_context = ActionContext(agent_registry = registry, 
                               debug = DEBUG,
                               ui_option = "streamlit",
                               properties = {
                                   "GOOGLE_SEARCH_API_KEY": st.secrets["GOOGLE_SEARCH_API_KEY"],
                                   "GOOGLE_SEARCH_ENGINE_ID": st.secrets["GOOGLE_SEARCH_ENGINE_ID"],
                                   "GS_CREDENTIALS": json.loads(st.secrets["GS_CREDENTIALS"])
                               })


# 3. Main function for chat session
def main():
    
    st.title("README Writer Agent")

    render_sidebar(registry)

            
                

    # 1. Initialization session state for shared memory
    if "shared_memory" not in st.session_state:
        st.session_state.shared_memory = Memory(max_history=MAX_HISTORY)
    
    
    # 2. Introduction message 
    if st.session_state.shared_memory.get_memories() == []:
        intro_message = "Hello! Paste a **remote github repository url** to analyze. Please make sure that the repository is **public accessible.**"
        with st.chat_message("assistant"):
            st.success(intro_message)

    # 3. History messages display: st.chat_message
    for msg in st.session_state.shared_memory.get_memories():
        if msg["role"] == "user":
            if isinstance(msg["content"], str) and '"tool_executed":' in msg['content']:
                continue
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            if msg['content']:           # avoid printing empty string
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

    # 4. User input
    if user_query := st.chat_input("Assign a job...", on_submit = set_session_running):
        
        with st.chat_message("user"):
            st.markdown(user_query)

        # 4. Call the agent. Update the shared_memory whenever there's a new response
        with st.chat_message("assistant"):

            @handle_running_session
            def agent_running():
                with st.spinner("Agent Thinking..."):
                    context_manager = st.expander("Expand to see the thinking process") if DEBUG else st.container()
                    with context_manager:
                        # Update shared memory
                        st.session_state.shared_memory = manager_agent.run(
                            user_query, 
                            memory=st.session_state.shared_memory, 
                            action_context=action_context, 
                            debug=DEBUG,
                            ui_option=action_context.ui_option
                        )
                    
                    
                # Get last assistant message
                last_msg = "Error. Failed to get response."
                for item in reversed(st.session_state.shared_memory.get_memories()):
                    if (item.get("role") == "assistant") and (item.get("content")):
                        last_msg = item.get("content")
                        break
                st.write_stream(stream_data(last_msg))
                if "README" in st.session_state:
                    st.markdown(st.session_state['README'])
                    st.session_state.shared_memory.add_memory({
                        "role": "assistant", "content": st.session_state['README']
                    })
                    st.session_state.global_memory.append({
                        "agent_session": manager_agent.name,
                        "role": "assistant", "content": st.session_state['README']
                    })

            agent_running()
            st.rerun()



if __name__ == "__main__":
    main()