from litellm import completion
from typing import List, Dict
from components.game import Prompt
import os
from dotenv import load_dotenv
load_dotenv()

os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY")


def generate_response(prompt: Prompt):
    """
    Call LLM and return message that contents both tool usage and chat content
    """
    response = completion(
        model="openrouter/minimax/minimax-m3.1-flash:free",
        messages=prompt.messages,
        max_tokens=4000,
        tools=prompt.tools if prompt.tools else None # 確保沒有工具時傳 None
    )
    
    # 直接回傳 Message 物件，這是 LiteLLM 內部的標準格式
    # 它包含了 .content 和 .tool_calls
    return response.choices[0].message