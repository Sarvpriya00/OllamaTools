import os
import json
import subprocess
import requests
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

# TOOL DESCRIPTION SYSTEM
TOOL_METADATA = {
    "read_file": {
        "name": "read_file",
        "description": "Read the complete contents of a file.",
        "parameters": {
            "path": "The absolute or relative path to the file."
        },
        "returns": "The content of the file or an error message.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'read_file(path="docs/readme.txt")'
    },
    "write_file": {
        "name": "write_file",
        "description": "Create a new file or overwrite an existing file with content.",
        "parameters": {
            "path": "The path to the file.",
            "content": "The exact content to write."
        },
        "returns": "Success or error message.",
        "risk_level": "medium",
        "requires_approval": False,
        "usage_example": 'write_file(path="test.py", content="print(\'Hello\')")'
    },
    "edit_file": {
        "name": "edit_file",
        "description": "Find and replace a specific string within a file.",
        "parameters": {
            "path": "The path to the file.",
            "find": "The exact text to find.",
            "replace": "The new text to insert."
        },
        "returns": "Success or error message.",
        "risk_level": "medium",
        "requires_approval": False,
        "usage_example": 'edit_file(path="main.py", find="old_val", replace="new_val")'
    },
    "list_files": {
        "name": "list_files",
        "description": "List files and directories in the specified directory.",
        "parameters": {
            "directory": "The path to the directory."
        },
        "returns": "A listing of files/directories.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'list_files(directory=".")'
    },
    "create_directory": {
        "name": "create_directory",
        "description": "Create a new directory.",
        "parameters": {
            "path": "The path of the directory to create."
        },
        "returns": "Success or error message.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'create_directory(path="new_folder")'
    },
    "rename_file": {
        "name": "rename_file",
        "description": "Rename or move a file or directory.",
        "parameters": {
            "old_path": "The current path.",
            "new_path": "The new path."
        },
        "returns": "Success or error message.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'rename_file(old_path="old.txt", new_path="new.txt")'
    },
    "delete_file": {
        "name": "delete_file",
        "description": "Delete a file or directory. REQUIRES APPROVAL.",
        "parameters": {
            "path": "The path of the file or directory to delete.",
            "approved": "boolean - Must be True to proceed."
        },
        "returns": "Success, failure, or approval request.",
        "risk_level": "high",
        "requires_approval": True,
        "usage_example": 'delete_file(path="unused.txt", approved=True)'
    },
    "search_in_files": {
        "name": "search_in_files",
        "description": "Search for a text query within all files in a directory.",
        "parameters": {
            "directory": "The directory to search in.",
            "query": "The text to search for."
        },
        "returns": "Search results.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'search_in_files(directory="src", query="TODO")'
    },
    "run_bash": {
        "name": "run_bash",
        "description": "Execute a bash command. Potentially dangerous commands require approval.",
        "parameters": {
            "command": "The bash command to execute.",
            "approved": "boolean - Required if the command is flagged as dangerous."
        },
        "returns": "Command output, error, or approval request.",
        "risk_level": "medium",
        "requires_approval": False, # conditionally True
        "usage_example": 'run_bash(command="ls -la", approved=False)'
    },
    "web_search": {
        "name": "web_search",
        "description": "Perform a simple web search.",
        "parameters": {
            "query": "The search query."
        },
        "returns": "Snippets of search results.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'web_search(query="python requests tutorial")'
    },
    "fetch_url": {
        "name": "fetch_url",
        "description": "Fetch and return the text content of a URL.",
        "parameters": {
            "url": "The URL to fetch."
        },
        "returns": "Text content of the URL.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'fetch_url(url="https://example.com")'
    },
    "download_file": {
        "name": "download_file",
        "description": "Download a file from an internet URL to a local path. REQUIRES APPROVAL.",
        "parameters": {
            "url": "The URL to download.",
            "path": "The local file path to save it to.",
            "approved": "boolean - Must be True to proceed."
        },
        "returns": "Success or error message.",
        "risk_level": "high",
        "requires_approval": True,
        "usage_example": 'download_file(url="https://example.com/file.zip", path="downloads/file.zip", approved=True)'
    },
    "parse_json": {
        "name": "parse_json",
        "description": "Parse a JSON string to ensure valid structure and format it.",
        "parameters": {
            "text": "The JSON string to parse."
        },
        "returns": "Pretty-printed JSON string.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'parse_json(text="{\\"key\\": \\"value\\"}")'
    },
    "list_tools": {
        "name": "list_tools",
        "description": "Returns a formatted JSON list of all available tools and their metadata.",
        "parameters": {},
        "returns": "JSON string containing tool metadata.",
        "risk_level": "low",
        "requires_approval": False,
        "usage_example": 'list_tools()'
    }
}

def list_tools() -> str:
    """Return a formatted JSON string listing ALL tools and their metadata."""
    return json.dumps(TOOL_METADATA, indent=2)

DANGEROUS_COMMANDS = [
    "rm", "sudo", "curl", "wget", "chmod", "chown",
    "mv", "mkfs", "dd", "fdisk", "reboot", "shutdown",
    ">", ">>", "|"
]

def _is_command_safe(command: str) -> bool:
    """Check if a bash command is safe to run without user approval."""
    command_lower = command.lower()
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in command_lower.split() or dangerous in command_lower:
            return False
    return True

def read_file(path: str) -> str:
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def write_file(path: str, content: str) -> str:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: File '{path}' written successfully."
    except Exception as e:
        return f"Error writing file '{path}': {str(e)}"

def edit_file(path: str, find: str, replace: str) -> str:
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if find not in content:
            return f"Error: The exact search string was not found in '{path}'."
        new_content = content.replace(find, replace)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f"Success: File '{path}' edited successfully."
    except Exception as e:
        return f"Error editing file '{path}': {str(e)}"

def list_files(directory: str) -> str:
    try:
        if not os.path.exists(directory):
            return f"Error: Directory '{directory}' does not exist."
        items = list(Path(directory).iterdir())
        res = []
        for item in items:
            type_str = "DIR " if item.is_dir() else "FILE"
            res.append(f"[{type_str}] {item.name}")
        return "\n".join(res) if res else "Directory is empty."
    except Exception as e:
        return f"Error listing directory '{directory}': {str(e)}"

def create_directory(path: str) -> str:
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"Success: Directory '{path}' created successfully."
    except Exception as e:
        return f"Error creating directory '{path}': {str(e)}"

def rename_file(old_path: str, new_path: str) -> str:
    try:
        if not os.path.exists(old_path):
            return f"Error: '{old_path}' does not exist."
        Path(new_path).parent.mkdir(parents=True, exist_ok=True)
        Path(old_path).rename(new_path)
        return f"Success: Renamed '{old_path}' to '{new_path}'."
    except Exception as e:
        return f"Error renaming '{old_path}': {str(e)}"

def delete_file(path: str, approved: bool = False) -> str:
    if not approved:
        return f"APPROVAL_REQUIRED: User must approve deletion of '{path}'."
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: '{path}' does not exist."
        if p.is_dir():
            shutil.rmtree(p)
            return f"Success: Directory '{path}' deleted."
        else:
            p.unlink()
            return f"Success: File '{path}' deleted."
    except Exception as e:
        return f"Error deleting '{path}': {str(e)}"

def search_in_files(directory: str, query: str) -> str:
    try:
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return f"Error: Directory '{directory}' does not exist or is not a directory."
        results = []
        for filepath in dir_path.rglob('*'):
            if filepath.is_file():
                try:
                    content = filepath.read_text(encoding='utf-8')
                    if query in content:
                        results.append(f"Match found in: {filepath}")
                except UnicodeDecodeError:
                    pass
                except Exception:
                    pass
        return "\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"Error searching in directory '{directory}': {str(e)}"

def run_bash(command: str, approved: bool = False) -> str:
    is_safe = _is_command_safe(command)
    if not is_safe and not approved:
        return f"APPROVAL_REQUIRED: The command '{command}' is potentially dangerous."
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output.strip() if output.strip() else "Success: Command executed with no output."
    except subprocess.TimeoutExpired:
        return f"Error: Command '{command}' timed out after 30 seconds."
    except Exception as e:
        return f"Error running command '{command}': {str(e)}"

def web_search(query: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        snippets = []
        parts = response.text.split('class="result__snippet')
        for part in parts[1:6]:
            if '>' in part and '</a>' in part:
                snippet = part.split('>', 1)[1].split('</a>', 1)[0]
                clean = re.sub('<[^<]+>', '', snippet).strip()
                if clean:
                    snippets.append(clean)
        if not snippets:
            return "No obvious search results found."
        return "\n".join([f"- {s}" for s in snippets])
    except Exception as e:
        return f"Error searching web for '{query}': {str(e)}"

def fetch_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text[:5000]
    except Exception as e:
        return f"Error fetching URL '{url}': {str(e)}"

def download_file(url: str, path: str, approved: bool = False) -> str:
    if not approved:
        return f"APPROVAL_REQUIRED: Downloading from '{url}' to '{path}'."
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return f"Success: File downloaded to '{path}'."
    except Exception as e:
        return f"Error downloading from '{url}': {str(e)}"

def parse_json(text: str) -> str:
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error parsing JSON: {str(e)}"


# Central tool registry mapping string names to function references
TOOL_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
    "create_directory": create_directory,
    "rename_file": rename_file,
    "delete_file": delete_file,
    "search_in_files": search_in_files,
    "run_bash": run_bash,
    "web_search": web_search,
    "fetch_url": fetch_url,
    "download_file": download_file,
    "parse_json": parse_json,
    "list_tools": list_tools
}

def get_tool_schemas() -> list[dict]:
    """
    Generate tool schemas formatted for LLM tool calling dynamically from TOOL_METADATA.
    """
    schemas = []
    for tool_name, metadata in TOOL_METADATA.items():
        properties = {}
        required = []
        for param, desc in metadata["parameters"].items():
            # Assume boolean if the param is 'approved' or string says boolean
            if desc.startswith("boolean") or param == "approved":
                properties[param] = {"type": "boolean", "description": desc}
            else:
                properties[param] = {"type": "string", "description": desc}
            required.append(param)
            
        schemas.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": metadata["description"],
                "parameters": {
                    "type": "object",
                    "required": required,
                    "properties": properties
                }
            }
        })
    return schemas