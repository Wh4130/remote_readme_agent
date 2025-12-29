"""Implements the GAME structure of an AI Agent"""

from dataclasses import dataclass
import json
import inspect
import time 
import traceback
from typing import List, Callable, Dict, Any, Tuple, get_type_hints, Optional


# * Goal class
@dataclass(frozen=True)
class Goal:
    content: str

# * Prompt class
@dataclass
class Prompt:
    messages: List[Dict]
    tools: List[Dict]

# * Action class
class Action:
    def __init__(self,
                 name: str,
                 function: Callable,
                 description: str,
                 parameters: Dict,
                 terminal: bool = False,
                 tags: List[str] = []):
        self.name = name
        self.function = function
        self.description = description
        self.terminal = terminal
        self.parameters = parameters
        self.tags = tags

    def execute(self, action_context, **args) -> Any:
        """Execute the action's function"""
        return self.function(action_context = action_context, **args)

# * Action Registry
class ActionRegistry:
    def __init__(self):
        self.actions = {}
        self.actions_by_tag = {}

    def _get_json_type(self, python_type) -> str:
       """將 Python 型別映射至 JSON Schema 型別"""
       type_map = {
           str: "string",
           int: "number",
           float: "number",
           bool: "boolean",
           list: "array",
           dict: "object",
           Any: "string" # 預設值
       }
       return type_map.get(python_type, "string")
    
    def _auto_generate_params(self, func):
        """utility function to extract the metadata from a function"""
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Build JSON schema for arguments
        args_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        # Examine each parameter
        for param_name, param in signature.parameters.items():
            # Skip special parameters
            if param_name in ["action_context", "action_agent"]:
                continue

            # Convert Python types to JSON schema types
            param_type = type_hints.get(param_name, str)
            param_schema = {
                "type": self._get_json_type(param_type)
            }
            
            args_schema["properties"][param_name] = param_schema
            
            # If parameter has no default, it's required
            if param.default == inspect.Parameter.empty:
                args_schema["required"].append(param_name)

        return args_schema

    def register(self, action: Action):
        self.actions[action.name] = action

    def get_action(self, name: str) -> Action | None:
        return self.actions.get(name, None)

    def get_actions(self, tags: List[str] | None = None) -> List[Action]:
        """
        If no tag specified, return all available tools.
        Otherwise, filter available tools by tags
        """
        all_actions = list(self.actions.values())
        if not tags:
            return all_actions
        
        return [a for a in all_actions if any(t in getattr(a, 'tags', []) for t in tags)]

    
    def register_tool(self, tool_name=None, description=None, 
                      parameters_override=None, terminal=False, tags=None):
        """decorator: to register a function as a tool"""
        def decorator(func):
            # 1. fetch metadata of the function
            name = tool_name or func.__name__
            desc = description or (func.__doc__.strip() if func.__doc__ else "No description")
            
            # 這裡假設你有個輔助函式處理 inspect.signature
            params = parameters_override or self._auto_generate_params(func)
            
            # 2. 封裝成 Action 物件
            new_action = Action(
                name=name,
                function=func,
                description=desc,
                parameters=params,
                terminal=terminal,
                tags=tags or []
            )
            
            # 3. 呼叫內部的 register 方法存入字典
            self.register(new_action)

            # Also maintain a tag-based index
            for tag in new_action.tags:
                if tag not in self.actions_by_tag:
                     self.actions_by_tag[tag] = []
                self.actions_by_tag[tag].append(name)
            
            return func
        return decorator
    

# Aciton context
class ActionContext:
    """
    提供工具執行時所需的上下文環境。
    封裝了 LLM 呼叫、Agent 註冊表以及使用者配置。
    """
    def __init__(self, 
                 agent_registry: Any = None, 
                 llm_provider: Optional[Callable] = None,
                 properties: Optional[Dict[str, Any]] = None,
                 debug: bool = False,
                 ui_option: str = "cli"):
        self._agent_registry = agent_registry
        self._llm = llm_provider
        self._properties = properties or {}
        self.debug = debug
        self.ui_option = ui_option
        
    def get_agent_registry(self) -> Any:
        """獲取已註冊的 Agent 清單"""
        return self._agent_registry

    def get(self, key: str, default: Any = None) -> Any:
        """獲取特定配置或物件（如 'llm', 'auth_token'）"""
        if key == "llm":
            return self._llm
        return self._properties.get(key, default)
    
class Memory:
    def __init__(self, max_history=20):
        self.items = []
        self.max_history = max_history

    def add_memory(self, item: dict):
        self.items.append(item)

    def get_memories(self, limit: int| None = None) -> List[Dict]:
        # 只取最近的 N 則紀錄，避免 Token 爆炸
        limit = limit or self.max_history
        return self.items[-limit:]
    
class Environment:
    def execute_action(self, action: Action, action_context: ActionContext, args: dict) -> dict:
        """Execute an action and return the result."""
        try:
            result = action.execute(action_context = action_context, **args)
            return self.format_result(result)
        except Exception as e:
            return {
                "tool_executed": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    def format_result(self, result: Any) -> dict:
        """Format the result with metadata."""
        return {
            "tool_executed": True,
            "result": result,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
        }
    

# * AgentLanguage Interface
"""
1. construct prompt
2. parse response
"""
class AgentFunctionCallingActionLanguage:
    def format_goals(self, goals: List[Goal]):
        # 建議將目標合併成一個 system message 或是置頂
        descriptions = [g.content for g in goals]
        return [{"role": "system", "content": f"Main Goals: {'; '.join(descriptions)}"}]

    def format_memory(self, memory: Memory):
        return memory.get_memories()

    def format_actions(self, actions: List[Action]) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": action.name,
                    "description": action.description[:1024],
                    "parameters": action.parameters,
                },
            } for action in actions
        ]

    def construct_prompt(self, actions: List[Action], environment: Any, 
                         goals: List[Goal], memory: Memory) -> Prompt:
        prompt_msgs = []
        prompt_msgs += self.format_goals(goals)
        prompt_msgs += self.format_memory(memory)
        tools = self.format_actions(actions)
        return Prompt(messages=prompt_msgs, tools=tools)

    def parse_response(self, response: Any) -> dict:
        # 假設 response 是 Message 物件
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0].function
            tool_name = tool_call.name
            
            try:
                raw_args = json.loads(tool_call.arguments)
            except json.JSONDecodeError:
                raw_args = {}

            # --- 核心修復：處理 Cerebras 的包裹行為 ---
            # 如果 raw_args 長得像 {"args": {...}} 或 {"arguments": {...}}
            if isinstance(raw_args, dict) and len(raw_args) == 1:
                potential_key = next(iter(raw_args))
                if potential_key in ["args", "arguments", "parameters"]:
                    # 確保裡面真的是另一個 dict 或是空的
                    if isinstance(raw_args[potential_key], dict):
                        raw_args = raw_args[potential_key]
            
            return {
                "tool": tool_name,
                "args": raw_args
            }

        # 處理 Final Answer
        return {
            "tool": None, 
            "args": {"content": getattr(response, 'content', str(response))}
        }