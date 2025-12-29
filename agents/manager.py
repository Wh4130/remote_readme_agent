import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.game import * 
from components.frame import Agent, AgentFunctionCallingActionLanguage, AgentRegistry, ActionContext
from components.model import generate_response

from agents.file_management_agent import file_management_agent


"""
agent file structure:

- initialize required components (language, environment, action_registry)
- (*) define a 'call_agent" function for the manager agent to invoke other sub-agents
- register all tools in action_registry
- create agent instance with components
"""


# ----------------------------------------------------------
# * Initialization
action_registry = ActionRegistry()
goals = [
    Goal("You are a project manager in a software development team. Your task is to delegate tasks to specialized sub-agents based on user requests and compile their results."),
    Goal("Effectively utilize the 'call_agent' tool to assign tasks to the appropriate sub-agents and gather their outputs."),
    Goal("Do not include any JSON format when you are simply replying my question without calling a tool.")
]
language = AgentFunctionCallingActionLanguage()
environment = Environment()

# ----------------------------------------------------------
# * call_agent tool design
# ! function that calls other agent. only available for manager agent

@action_registry.register_tool(
    tool_name="call_agent",
    description="",)
def call_agent(action_context: ActionContext, agent_name: str, task: str):
    """
    Invoke another agent to perform a specific task.
    
    Args:
        action_context: Contains registry of available agents
        agent_name: Name of the agent to call
        task: The task to ask the agent to perform
        
    Returns:
        The result from the invoked agent's final memory
    """

    # * Get the agent registry from our context
    agent_registry = action_context.get_agent_registry()
    if not agent_registry:
        raise ValueError("No agent registry found in context")
    
    # * Get the agent's run function from the registry
    agent_run = agent_registry.get_agent(agent_name)
    if not agent_run:
        raise ValueError(f"Agent '{agent_name}' not found in registry")
    
    # * Create a new memory instance for the invoked agent
    invoked_memory = Memory()
    
    try:
        # Run the agent with the provided task
        result_memory = agent_run(
            user_input=task,
            memory=invoked_memory,
            # Pass through any needed context properties
            action_context=action_context,
            debug=action_context.debug,
            ui_option=action_context.ui_option
        )
        
        # * Get the last assistant memory item as the result
        if result_memory.items:
            # find the last assistant message
            last_assistant_memory = "No assistant message found."
            for item in reversed(result_memory.get_memories()):
                if (item.get("role") == "assistant") and (item.get("content")):
                    last_assistant_memory = item.get("content")
                    break
            return {
                "success": True,
                "agent": agent_name,
                "result": last_assistant_memory
            }
        else:
            return {
                "success": False,
                "error": "Agent failed to run."
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


    return 


# ----------------------------------------------------------
# * Tool Registration



# ----------------------------------------------------------
# * Agent Creation
manager_agent = Agent("manager_agent", goals, language, action_registry, generate_response, environment)
