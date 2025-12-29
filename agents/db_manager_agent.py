import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.game import * 
from components.frame import Agent, AgentFunctionCallingActionLanguage, AgentRegistry, ActionContext
from components.model import generate_response
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
    "You are a Google Sheet database manager. You could open a new worksheet and insert any data into it. However, you are not able to modify an existing worksheet."
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

def get_gsheet_obj(action_context: ActionContext, google_sheet_url, *args, **kwargs):
    # authenticate
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(action_context.get("GS_CREDENTIALS"), scope)
    client = gspread.authorize(creds)
    
    # get id
    try:
        gs_id = google_sheet_url.split("/d/")[1].split("/")[0]
    except IndexError:
        return {"error": "Invalid Google Sheet URL"}

    # get google sheet
    try:
        gsheet = client.open_by_key(gs_id)
    except:
        return {"error": "Invalid Google Sheet URL"}
    
    return gsheet


@action_registry.register_tool(
    tool_name="create_worksheet",
    description="Create a new worksheet in the specified google sheet. You need to provide the google sheet link and the name of the worksheet.",
    tags = ["database"])
def create_new_worksheet(action_context: ActionContext, google_sheet_url, worksheet_name, col_num, row_num, *args, **kwargs):
    gsheet = get_gsheet_obj(action_context, google_sheet_url)
    if "error" in gsheet:
        return gsheet 

    
    try:
        worksheet = gsheet.worksheet(worksheet_name)
        return {"error": "Worksheet already exists. Try another name."}
    except gspread.WorksheetNotFound:
        worksheet = gsheet.add_worksheet(
            title=worksheet_name,
            rows=row_num, 
            cols=col_num
        )
    return {"success": f"Worksheet {worksheet_name} created successfully."}


@action_registry.register_tool(
    tool_name="insert_data_into_googlesheet",
    description="Insert data into google sheet. You need to specify the url, worksheet name, header (as a list), and values (as a list of lists)",
    tags = ["database"])
def insert_data_into_googlesheet(action_context: ActionContext, google_sheet_url, worksheet_name, header_row, values, *args, **kwargs):

    gsheet = get_gsheet_obj(action_context, google_sheet_url)
    if "error" in gsheet:
        return gsheet 
    try:
        worksheet = gsheet.worksheet(worksheet_name)
    except:
        return {"error": "Worksheet does not exist."}
    worksheet.append_row(header_row)
    worksheet.freeze(rows = 1)
    worksheet.append_rows(values)

    return {"success": f"Data inserted into {worksheet_name} successfully."}
        


# ----------------------------------------------------------
# * Register Public Tools
for public_action in public_tools_registry.get_actions(tags):
    action_registry.register(public_action)



# ----------------------------------------------------------
# * Agent Creation
google_sheet_agent = Agent("google_sheet_agent", goals, language, action_registry, generate_response, environment)