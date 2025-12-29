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
from utils_st import stream_data, render_global_memory

# Configuration
# variables with all capital letters are constants in the config file 
from config import *

import streamlit as st
import time, json
from dotenv import dotenv_values


if "global_memory" not in st.session_state:
        st.session_state["global_memory"] = []

# TODO 1. Construct Agent Registry and register all sub-agents
registry = AgentRegistry()
# registry.register_agent(writer_agent.name, writer_agent.run)
registry.register_agent(web_search_agent.name, web_search_agent.run)
registry.register_agent(google_sheet_agent.name, google_sheet_agent.run)

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

    with st.sidebar:
        st.header("README Writer Agent")
        st.caption("A multi-agent system that analyzes a remote git repository and writes a README.md file. Start using it by pasting a :blue[**public remote github repository url.**]")
        st.logo("assets/icon.png", size = 'large')
        st.divider()
        with st.container(border = True):
            
            st.write(":material/support_agent: **Sub-agent List**")
            st.dataframe(registry.agents.keys())

            st.write(":material/memory: **Analyze Global Memory**")
            st.caption(":red[Clicking this button will interrupt any running session.]")
            if st.button("Click to open", width = "stretch"):
                render_global_memory()

            st.write(":material/output_circle: **Most Recent Result**")
            if "README" in st.session_state:
                st.download_button(
                    label = "README.md",
                    data = st.session_state.README,
                    file_name = "README.md",
                    icon = ":material/download:",
                    width = "stretch",
                    key = f"{time.time()}"
                )
            else:
                st.warning("No result yet.")
                

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
    if user_query := st.chat_input("Assign a job..."):
        
        with st.chat_message("user"):
            st.markdown(user_query)

        # 4. Call the agent. Update the shared_memory whenever there's a new response
        with st.chat_message("assistant"):
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


        st.rerun()



if __name__ == "__main__":
    main()