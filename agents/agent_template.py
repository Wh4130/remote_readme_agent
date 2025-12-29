import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.game import * 
from components.frame import Agent, AgentFunctionCallingActionLanguage, AgentRegistry, ActionContext
from components.model import generate_response
import os

from public_tools import public_tools_registry


"""
agent file structure:

- initialize required components (language, environment, action_registry)
- register all tools in action_registry
- register public tools (could be filtered by tags) in action_registry
- create agent instance with components
"""

SYSTEM_PROMPTS = [
    # please insert your system prompt here
]
"""
Specify tags for this agent to filter public tools.
If empty, all public tools will be registered.
Execute 'python public_tools.py' in your terminal to see available actions catagorized by tags.
"""
tags = [] 

# ----------------------------------------------------------
# * Initialization        
action_registry = ActionRegistry()
goals = [
    Goal(system_prompt) for system_prompt in SYSTEM_PROMPTS
]
language = AgentFunctionCallingActionLanguage()
environment = Environment()

# ----------------------------------------------------------
# * Tool Registration

@action_registry.register_tool(
    tool_name="list_working_directory",
    description="Lists the current working directory",
    tags = ["file_operations"])
def list_working_directory(action_context: ActionContext):
    return os.getcwd()


@action_registry.register_tool(
    tool_name="list_files",
    description="Lists the files in the designated directory",
    tags = ["file_operations"])
def pwd_ls(action_context: ActionContext, dir_path):
    return os.listdir(dir_path)

@action_registry.register_tool(
    tool_name="analyze_files",
    description="Analyze the specified file",
    tags = ["file_operations"])
def analyze_file(action_context: ActionContext, file_path):
    with open(file_path, "r") as f:
        content = f.read()

    return content

@action_registry.register_tool(
    tool_name="construct_receipt",
    description="construct the receipt into json format with specific fields",
    tags = ["accounting"]
)
def organize_receipt(action_context: ActionContext, item: str, price: float, date: str, total_expense: float):
    record = {
        "item": item,
        "price": price,
        "date": date,
        "total_expense": total_expense
    }
    
    # 使用 'a' (append) 模式開啟
    # 指定 encoding="utf-8" 確保中文正常顯示
    with open("accounting.jsonl", "a", encoding="utf-8") as file:
        # ensure_ascii=False 讓中文直接存成文字而非編碼
        line = json.dumps(record, ensure_ascii=False)
        # 關鍵：每一筆紀錄後必須手動加上 \n 換行符號
        file.write(line + "\n")
        
    return {"status": "success", "message": f"Successfully recorded {item}"}

# ----------------------------------------------------------
# * Register Public Tools
for public_action in public_tools_registry.get_actions(tags):
    action_registry.register(public_action)



# ----------------------------------------------------------
# * Agent Creation
file_management_agent = Agent("file_management_agent", goals, language, action_registry, generate_response, environment)