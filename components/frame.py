from components.game import Goal, Prompt, Action, ActionRegistry, Memory, Environment, AgentFunctionCallingActionLanguage, ActionContext
from utils_st import add_global_memory

import json
import time
import streamlit as st
from typing import List, Callable, Dict, Any, Tuple, Optional
 

    
class Agent:
    def __init__(
        self,
        name: str,
        goals: List[Goal],
        agent_language: AgentFunctionCallingActionLanguage,
        action_registry: ActionRegistry,
        generate_response: Callable[[Prompt], str],
        environment: Environment,
        tags = None
    ):
        """
        Initialize an agent with its core GAME components
        """
        self.name = name
        self.goals = goals
        self.generate_response = generate_response
        self.agent_language = agent_language
        self.actions = action_registry
        self.environment = environment
        self.tags = tags

    def construct_prompt(self, goals: List[Goal], memory: Memory, actions: ActionRegistry) -> Prompt:
        """Build prompt with memory context"""
        return self.agent_language.construct_prompt(
            actions=actions.get_actions(self.tags),
            environment=self.environment,
            goals=goals,
            memory=memory
        )

    def get_action(self, response):
        invocation = self.agent_language.parse_response(response)
        
        # 如果 parse_response 沒抓到工具 (例如 invocation["tool"] 是 None 或 "final_answer")
        if not invocation or not invocation.get("tool"):
            return None, invocation
            
        action = self.actions.get_action(invocation["tool"])
        return action, invocation
    

    

    def should_terminate(self, response: str) -> bool:
        action_def, invocation = self.get_action(response)
        
        # 情況 1：如果 LLM 沒有呼叫任何工具，代表它在直接對話，通常視為任務結束
        if action_def is None:
            # 如果你想讓 Agent 在說話時就停下來，這裡回傳 True
            return True 
        
        # 情況 2：如果找到了工具，則根據該工具是否標記為 terminal 來決定
        return getattr(action_def, 'terminal', False)

    def set_current_task(self, memory: Memory, task: str):
        """Inject the user's initial request into memory"""
        memory.add_memory({"role": "user", "content": task})

    def set_current_task_global(self, content: str):
        """update the task to global memories"""
        add_global_memory(self.name, {"role": "user", "content": content, "time": f"{time.time()}"})

    def update_memory(self, memory: Memory, response: Any, result: dict):
        # 此時的 response 是 Message 物件
        # 將其轉換為 dict 存入記憶體
        assistant_mem = {
            "role": "assistant",
            "content": response.content or ""
        }
        if hasattr(response, 'tool_calls') and response.tool_calls:
            assistant_mem["tool_calls"] = response.tool_calls

        memory.add_memory(assistant_mem)
        memory.add_memory({"role": "user", "content": json.dumps(result)})

    def update_memory_global(self, result: dict | Any, role: str):
        assert role in ['user', 'assistant'], "role must be 'user' or 'assistant'"
        if role == "assistant":
            assistant_mem = {
                "role": role,
                "content": result.content or "",
                "time": f"{time.time()}"
            }
            if hasattr(result, 'tool_calls') and result.tool_calls:
                assistant_mem["tool_calls"] = result.tool_calls

            add_global_memory(self.name, assistant_mem)
        else:
            add_global_memory(self.name, {"role": role, 
                                          "content": json.dumps(result),
                                          "time": f"{time.time()}"})

    

    def prompt_llm_for_action(self, full_prompt: Prompt) -> str:
        """Call the provided LLM function"""
        response = self.generate_response(full_prompt)
        return response
    
    def debugging(self, ui_option, message):
        if ui_option == "streamlit":
            st.write(message)
        else:
            print(message)

    def run(self, user_input: str, memory=None, max_iterations: int = 50, action_context: ActionContext | None = None, debug = False, ui_option = "cli") -> Memory:
        """
        Execute the GAME loop for this agent with a maximum iteration limit.
        """

        # set up memory
        memory = memory or Memory()
        self.set_current_task(memory, user_input)
        self.set_current_task_global(user_input)

        # dynamically modify the description of 'call_agent' tool (for manager agent) if exists
        registry, call_agent_tool = None, None
        if action_context is not None:
            registry = action_context.get_agent_registry()
        call_agent_tool = self.actions.get_action("call_agent")
        if call_agent_tool and registry:
            names = list(registry.agents.keys())
            call_agent_tool.description = f"Call another agent to finish a task. List of available agents: {names}"


        for _ in range(max_iterations):
            # 1. Construct a prompt that includes the Goals, Actions, and the current Memory
            prompt = self.construct_prompt(self.goals, memory, self.actions)
            if debug:
                self.debugging(ui_option, f">({self.name}) Agent thinking...\n")
                

            # 2. Generate a response from the agent and update the result to global
            response = self.prompt_llm_for_action(prompt)
            self.update_memory_global(response, role = "assistant")
            if debug:
                self.debugging(ui_option, f">({self.name}) Agent Decision: {response}\n")

            # 3. Determine which action the agent wants to execute
            action, invocation = self.get_action(response)

            # 4. Execute the action in the environment
            if invocation['tool'] is None:        # --> LLM is talking, not using tools
                result = {
                    "tool_executed": False, 
                    "message": "LLM chose to respond without using a tool."
                }
            else:                                 # --> LLM is calling a tool
                if action is None:
                    # * the tool does not exist
                    result = {
                        "tool_executed": False, 
                        "error": f"Tool '{invocation['tool']}' does not exist. Please check your available tools."
                    }
                else:
                    # * the tool exists, execute it
                    result = self.environment.execute_action(action, action_context, invocation["args"])
                    if debug:
                        self.debugging(ui_option, f">({self.name}) Action Result: {result}\n")

            # 5. Update the agent's memory with information about what happened
            self.update_memory(memory, response, result)
            self.update_memory_global(result, role = "user")

            # 6. Check if the agent has decided to terminate
            if self.should_terminate(response):
                break

        return memory
    

class AgentRegistry:
    def __init__(self):
        self.agents = {}
        
    def register_agent(self, name: str, run_function: Callable):
        """Register an agent's run function."""
        self.agents[name] = run_function
        
    def get_agent(self, name: str) -> Callable:
        """Get an agent's run function by name."""
        return self.agents.get(name)




