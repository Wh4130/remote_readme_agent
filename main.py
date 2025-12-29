# Import manager agent from agents folder
from agents.manager import manager_agent

# TODO Import sub-agents from agents folder
from agents.agent import file_management_agent

# Import necessary components
from components.game import ActionContext, Goal, Action, ActionRegistry, Memory
from components.frame import AgentRegistry, Agent

# Configuration
# variables with all capital letters are constants in the config file 
from config import *



# TODO 1. Construct Agent Registry and register all sub-agents
registry = AgentRegistry()
registry.register_agent("agent_template", file_management_agent.run)


# 2. Construct ActionContext instance
# Note: This is where the Registry is actually passed in
action_context = ActionContext(agent_registry = registry, 
                               debug = DEBUG,
                               ui_option = "cli")


# 3. Main function for chat session
# ! IMPORTANT NOTES
# - There are two UI options: Command Line Interface (CLI) and Streamlit Web App.
#   You can choose either based on your preference.
#     - If you are using CLI, execute 'python main.py' in terminal
#     - If you are using Streamlit, execute 'streamlit run main.py' in terminal
# - Also remember to modify the UI_OPTION variable in config.py accordingly

def main():

    shared_memory = Memory(max_history = MAX_HISTORY) 

    while True:
        user_query = input("User: ")
        if user_query.lower() in ["exit", "quit"]:
            break
            
        # use the global shared memory and update it every iteration
        shared_memory = manager_agent.run(user_query, 
                                  memory = shared_memory, 
                                  action_context = action_context, 
                                  debug = DEBUG,
                                  ui_option = action_context.ui_option)
        
        # print the last assistant message
        # -1: user (result of tool execution)
        # -2: assistant
        last_msg = shared_memory.get_memories()[-2] 
        print(f"Agent: {last_msg['content']}")

if __name__ == "__main__":
    main()