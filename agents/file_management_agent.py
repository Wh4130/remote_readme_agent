import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.game import * 
from components.frame import Agent, AgentFunctionCallingActionLanguage, AgentRegistry, ActionContext
from components.model import generate_response

from public_tools import public_tools_registry
import os

"""
agent file structure:

- initialize required components (language, environment, action_registry)
- register all tools in action_registry
- register public tools (could be filtered by tags) in action_registry
- create agent instance with components
"""

# ----------------------------------------------------------
# * Initialization
tags = ["file_operations"]            # specify tags for this agent to filter public tools

action_registry = ActionRegistry()
goals = [
    Goal("You are a secretary manager. You can perform various file operations and web scraping tasks  based on user requests."),
]
language = AgentFunctionCallingActionLanguage()
environment = Environment()

# ----------------------------------------------------------
# * Tool Registration




# ----------------------------------------------------------
# * Register Public Tools
for public_action in public_tools_registry.get_actions(tags):
    action_registry.register(public_action)



# ----------------------------------------------------------
# * Agent Creation
file_management_agent = Agent("file_management_agent", goals, language, action_registry, generate_response, environment)