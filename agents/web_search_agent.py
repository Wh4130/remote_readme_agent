import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.game import * 
from components.frame import Agent, AgentFunctionCallingActionLanguage, AgentRegistry, ActionContext
from components.model import generate_response
import os

from public_tools import public_tools_registry


import tempfile
import subprocess
import os
import shutil
import requests

"""
agent file structure:

- initialize required components (language, environment, action_registry)
- register all tools in action_registry
- register public tools (could be filtered by tags) in action_registry
- create agent instance with components
"""

SYSTEM_PROMPTS = [
    # please insert your system prompt here
    "You are a competent secretary that gather information from web pages. You can implement google search, fetch the HTML source from a url, or even gather the content of a github remote repository.",

    "Do not rewrite any result from the information gathering process. Return the raw retrieved result to the user / manager agent."
]
"""
Specify tags for this agent to filter public tools.
If empty, all public tools will be registered.
Execute 'python public_tools.py' in your terminal to see available actions catagorized by tags.
"""
tags = ["web_scraping"] 

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
    tool_name="google_search",
    description="Implement google search and return a list of result URLs. You should pass the search keywords as a list and specify the number of returned results."
)
def google_search(action_context, search_keyword, num_results, *args, **kwargs):
    url = "https://www.googleapis.com/customsearch/v1"

    api_key = action_context.get("GOOGLE_SEARCH_API_KEY")
    engine_id = action_context.get("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key:
        return {"error": "Google Search API key not specified."}
    if not engine_id:
        return {"error": "Google Search Engine ID is not specified."}

    response = requests.get(url, params = {
        "key": api_key,
        "cx": engine_id,
        "q": search_keyword,
        "filter": 1,
        "num": num_results
    })

    return response.json()




@action_registry.register_tool(
    tool_name="get_github_repo_full_scan",
    description="Scan a git repository fully, excluding certain directories and file types, and return the content of the files and the directory structure.",)
def enhanced_full_scanner_tool(action_context, repo_url, *args, **kwargs):
    """
    scanner tool：
    1. exclude specific directories and extensions.
    2. load non-excluded files and concateneate contents to the report object
    3. content of each file is limited to 5000 words
    """
    tmp_dir = tempfile.mkdtemp(prefix="full_repo_scan_")
    report = []
    
    # 3. 排除特定 extension 與目錄
    exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'venv', 'node_modules', '.vscode'}
    exclude_exts = {
        '.png', '.jpg', '.jpeg', '.gif', '.ico',  # 圖片
        '.mp4', '.mp3', '.wav',                   # 影音
        '.zip', '.tar', '.gz', '.7z',             # 壓縮檔
        '.exe', '.bin', '.dll', '.so', '.pyc',    # 二進位
        '.DS_Store', '.env', '.pkl', '.model',    # 系統/模型/金鑰
        '.onnx', '.tflite', '.pb',                # 機器學習模型
        '.pdf', '.docx', '.xlsx', '.csv', '.parquet'                  
    }

    try:
        # 1. clone the git repo
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, tmp_dir],
            check=True, capture_output=True, text=True
        )
        
        report.append(f"=== REPOSITORY FULL SCAN: {repo_url} ===\n")

        # 2. 遞迴掃描所有內容
        for root, dirs, files in os.walk(tmp_dir):
            # 過濾排除目錄
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                
                # 3. 過濾排除副檔名
                if ext in exclude_exts or f in exclude_exts:
                    continue
                
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, tmp_dir)
                
                report.append(f"\n--- FILE: {rel_path} ---")
                
                try:
                    # 4. read contents
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as content_file:
                        content = content_file.read(5000)
                        if not content.strip():
                            report.append("[Empty File]")
                        else:
                            report.append(content)
                            if len(content) >= 2500:
                                report.append("\n[...CONTENT IS TOO LENGTHY. SLICED TO 5000 WORDS...]")
                except Exception as e:
                    report.append(f"[UNABLE TO READ FILE: {str(e)}]")
                
                report.append("-" * 40)

        return "\n".join(report)

    except Exception as e:
        return f"FAILED TO SCAN THE REPO: {str(e)}"
    finally:
        # Clean the temporary directory
        shutil.rmtree(tmp_dir)

# ----------------------------------------------------------
# * Register Public Tools
for public_action in public_tools_registry.get_actions(tags):
    action_registry.register(public_action)



# ----------------------------------------------------------
# * Agent Creation
web_search_agent = Agent("web_search_agent", goals, language, action_registry, generate_response, environment)