from components.game import * 
import os


public_tools_registry = ActionRegistry()


@public_tools_registry.register_tool(
    tool_name="list_files_in_a_directory",
    description="Lists the files in the designated directory",
    tags = ["file_operations"])
def pwd_ls(action_context, dir_path, *args, **kwargs):
    return os.listdir(dir_path)


@public_tools_registry.register_tool(
    tool_name="read_files",
    description="Read the content of specified file",
    tags = ["file_operations"])
def read_file(action_context, file_path, *args, **kwargs):
    with open(file_path, "r") as f:
        content = f.read()

    return content

@public_tools_registry.register_tool(
    tool_name="get_current_working_directory",
    description="Get the current working directory. This function does not take any argument. It only prints out the current working directory.",
    tags = ["file_operations"])
def get_cwd(action_context, *args, **kwargs):
    return os.getcwd()

@public_tools_registry.register_tool(
    tool_name="save_content_to_file",
    description="Save content to a file. You need to provide the content to be saved and the file path with correct extension..",
    tags = ["file_operations", "IO_save"])
def save_content_to_file(action_context, content, file_path, *args, **kwargs):
    with open(file_path, "w") as f:
        f.write(content)
    return f"Content saved to {file_path}"

@public_tools_registry.register_tool(
    tool_name="fetch_webpage_source",
    description="Fetch the webpage HTML content by requests module, and turn it to simple text by beautifulsoup. You need to provide the URL of the webpage.",
    tags = ["web_scraping"])
def web_search_tool(action_context, url, *args, **kwargs):
    """
    Scrape webpage source HTML 
    """
    import requests
    from bs4 import BeautifulSoup

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        for junk in soup(["script", "style", "nav", "footer", "header"]):
            junk.decompose()

        text = soup.get_text(separator='\n', strip=True)

        return text
    except Exception as e:
        return f"Failed scraping: {str(e)}"


if __name__ == "__main__":
    for tag, actions in public_tools_registry.actions_by_tag.items():
        print(f"> Tag: '{tag}'")
        print(f"  Actions:")
        for action_name in actions:
            print(f"   - {action_name}")
        
    