import argparse
import asyncio
import re
import warnings
import inspect
from typing import List, Optional
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS 
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# Muffle all verbose system warnings natively to preserve terminal UI UX
warnings.simplefilter("ignore", ResourceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

# Import the existing tool registry bridges safely exposing raw python components
import tools as sys_tools

class Colors:
    YOU = "\u001b[94m"          # Blue
    ASSISTANT = "\u001b[96m"    # Cyan
    ACTION = "\u001b[95m"       # Magenta
    FAIL = "\u001b[91m"         # Red
    BOLD = "\u001b[1m"
    OKCYAN = "\u001b[96m"
    RESET = "\u001b[0m"

# ==========================================
# 1. ContentFilter Class
# ==========================================
class ContentFilter:
    @staticmethod
    def filter_html(html_content: str, bypass: bool = False) -> str:
        soup = BeautifulSoup(html_content, "lxml")
        if bypass:
            return soup.get_text(separator='\n', strip=True)[:10000]
        tags_to_decompose = ['nav', 'header', 'footer', 'aside', 'img', 'video', 'iframe', 'script', 'style', 'canvas', 'svg']
        for tag in soup(tags_to_decompose):
            tag.decompose()
        spam_pattern = re.compile(r'ad|banner|promo|sponsor|newsletter|popup|sidebar', re.IGNORECASE)
        for tag in soup.find_all(True):
            classes = tag.get('class', [])
            tag_id = tag.get('id', '')
            class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)
            if spam_pattern.search(class_str) or spam_pattern.search(str(tag_id)):
                tag.decompose()
        clean_text = soup.get_text(separator='\n', strip=True)
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        return clean_text[:12000]

# ==========================================
# 2. Base Agent Tools (Functional System Triggers)
# ==========================================

@tool
def read_file(path: str) -> str:
    """Read the complete contents of a local file."""
    return sys_tools.read_file(path)

@tool
def write_file(path: str, content: str) -> str:
    """Create a new file or overwrite an existing file with string content."""
    return sys_tools.write_file(path, content)

@tool
def edit_file(path: str, find: str, replace: str) -> str:
    """Find and replace a specific string within a local file."""
    return sys_tools.edit_file(path, find, replace)

@tool
def list_files(directory: str) -> str:
    """List all files and directories in the specified local directory."""
    return sys_tools.list_files(directory)

@tool
def create_directory(path: str) -> str:
    """Create a new local directory."""
    return sys_tools.create_directory(path)

@tool
def rename_file(old_path: str, new_path: str) -> str:
    """Rename or move a local file or directory."""
    return sys_tools.rename_file(old_path, new_path)

@tool
def delete_file(path: str) -> str:
    """Delete a local file or directory. This tool is risky and requires explicit user confirmation."""
    return sys_tools.delete_file(path, approved=True)

@tool
def search_in_files(directory: str, query: str) -> str:
    """Search for a specific exact text query within all files in a directory."""
    return sys_tools.search_in_files(directory, query)

@tool
def run_bash(command: str) -> str:
    """Execute a bash command on the host machine. Risky commands require explicit user confirmation."""
    return sys_tools.run_bash(command, approved=True)

@tool
def parse_json(text: str) -> str:
    """Parse a raw JSON string to ensure valid structure and format it cleanly."""
    return sys_tools.parse_json(text)

@tool
def standard_web_search(query: str, max_results: int = 3) -> str:
    """Perform a simple web search using DuckDuckGo to return relevant URLs and snippet context. Does not scrape deep page data."""
    urls = []
    try:
        with DDGS() as ddgs:
            for backend in ["api", "lite", "html"]:
                try:
                    results = ddgs.text(query, max_results=max_results, backend=backend)
                    if results:
                        for r in results:
                            if isinstance(r, dict) and r.get('href'):
                                urls.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nDesc: {r.get('body')}")
                        if urls: break
                except Exception:
                    pass
        return "\n\n".join(urls)
    except Exception as e:
        return f"Web search error: {e}"

# Global map-reducer engine placeholder bridging tools safely
core_engine = None

async def isolated_scrape(url: str) -> str:
    try:
        browser_config = BrowserConfig(browser_type="chromium", headless=True, verbose=False)
        run_config = CrawlerRunConfig(word_count_threshold=10, wait_for="body")
        async with AsyncWebCrawler(config=browser_config) as crawler:
            res = await crawler.arun(url=url, config=run_config, bypass_cache=True)
            if res.success and res.html:
                return ContentFilter.filter_html(res.html)
            return "Extract Error"
    except Exception as e:
        return f"System Error: {e}"

@tool
async def perform_deep_research(goal: str) -> str:
    """Executes a massive, autonomous web-scale Deep Research Map-Reduce flow.
    Automatically generates search queries, scrapes pages, and maps them into technical summaries.
    Returns the highly synthesized research markdown string for you to analyze or save.
    Use this strictly when the user asks for deep analysis on a multifaceted topic.
    """
    print(f"  {Colors.ACTION}[Deep Research Engine Activated]{Colors.RESET} Synthesizing vectors for: {goal}")
    if not core_engine:
        return "Critical Error: Engine unresponsive."
        
    plan_prompt = PromptTemplate.from_template(
        "Decompose this research goal into exactly 3 to 5 distinct DuckDuckGo search queries.\n"
        "KEEP QUERIES BROAD to ensure search results.\n"
        "Output ONLY the queries, one per line.\n\n"
        "Goal: {goal}"
    )
    
    try:
        plan_res = core_engine.invoke(plan_prompt.format(goal=goal))
        queries = [q.strip() for q in plan_res.content.split('\n') if q.strip()][:3]
        print(f"  {Colors.ACTION}[Research Node]{Colors.RESET} Generated mapping queries...")
    except Exception as e:
        return f"Planning Fault: {e}"
        
    all_urls = set()
    for q in queries:
         try:
             res_string = standard_web_search.invoke({"query": q, "max_results": 2})
             urls = [line.replace("URL: ", "") for line in res_string.split('\n') if line.startswith('URL: ')]
             all_urls.update(urls)
         except: pass
         
    target_urls = list(all_urls)[:4] 
    if not target_urls:
         return "Deep Research Error: Network yielded 0 endpoints. Expand search scope."
         
    print(f"  {Colors.ACTION}[Research Node]{Colors.RESET} Located {len(target_urls)} endpoints, initiating deep scraping...")
    fetch_tasks = [isolated_scrape(u) for u in target_urls]
    raw_contents = await asyncio.gather(*fetch_tasks)
    
    valid_contents = [(u, txt) for u, txt in zip(target_urls, raw_contents) if len(txt) > 50 and "Error" not in txt[:20]]
    if not valid_contents:
        return "Deep Research Error: Target domains rejected automated scraping vectors."
        
    map_prompt = PromptTemplate.from_template(
        "Execute a dense, highly technical summary of the provided raw data. "
        "Keep within 300 words.\n\nRaw Data:\n{text}\n\nSynthesis:"
    )
    
    summaries = []
    print(f"  {Colors.ACTION}[Research Node]{Colors.RESET} Synthesizing discrete map layers...")
    for i, (source_url, text) in enumerate(valid_contents):
        try:
             res = core_engine.invoke(map_prompt.format(text=text))
             summaries.append(f"SOURCE_URL: {source_url}\n\nSUMMARY:\n{res.content}")
        except: pass
             
    print(f"  {Colors.ACTION}[Research Node]{Colors.RESET} Architecture successfully collapsed.")
    compiled_knowledge = "\n\n" + "="*40 + "\n\n".join(summaries)
    return f"Deep Research Synthesis Complete.\n\n{compiled_knowledge}"

# Aggregate Agent Tools
master_toolset = [
    read_file, write_file, edit_file, list_files, create_directory,
    rename_file, delete_file, search_in_files, run_bash, parse_json, 
    standard_web_search, perform_deep_research
]

# ==========================================
# 3. AgentSession (Stateful Controller)
# ==========================================

class AgentSession:
    def __init__(self, model: str):
        self.model = model
        self.core_engine = ChatOllama(model=model, base_url="http://localhost:11434", temperature=0, num_ctx=128000)
        self.agent_engine = self.core_engine.bind_tools(master_toolset)
        self.conversation = [
            SystemMessage(content=(
                "You are an autonomous AI coding assistant and research agent.\n"
                "You possess a dynamic tool registry that allows you to directly manipulate the file system (read_file, write_file, edit_file, run_bash), as well as perform web investigations.\n"
                "If a user asks you to write code or correct bugs, execute the necessary tools to navigate files and explicitly fix them independently.\n"
                "If a user asks for 'deep research' into a complex topic, you have a master tool `perform_deep_research`. Triggering it will silently perform complex scraping logic and pipe the summary text strictly into your context window. You can then save those findings via write_file or discuss them.\n"
                "Ensure all final responses respect the Apple Style Guide standard: direct, clear, free of fluff, and aggressively capability-oriented.\n"
                "If the user wants multiple files created, trigger multiple `write_file` sequences independently."
            ))
        ]

    async def run_turn(self, user_input: str, on_tool_call=None):
        """Processes one turn of the conversation, handling recursive tool calls."""
        self.conversation.append(HumanMessage(content=user_input))
        
        # Turn-level batch approval tracking
        batch_approve = False
        batch_reject = False
        
        while True:
            try:
                ai_msg = self.agent_engine.invoke(self.conversation)
            except Exception as e:
                print(f"{Colors.FAIL}Engine Fault: {e}{Colors.RESET}")
                return f"System Error: {e}"
                
            self.conversation.append(ai_msg)
            
            if not getattr(ai_msg, "tool_calls", None):
                return ai_msg.content
                
            for tool_call in ai_msg.tool_calls:
                t_name = tool_call.get("name")
                t_args = tool_call.get("args", {})
                
                # Protection Layer
                is_risky = False
                risky_msg = ""
                if t_name == "delete_file":
                    is_risky = True
                    risky_msg = f"delete '{t_args.get('path')}'"
                elif t_name == "run_bash":
                    cmd = t_args.get('command', '')
                    if not sys_tools._is_command_safe(cmd):
                        is_risky = True
                        risky_msg = f"run risky command: '{cmd}'"
                
                if is_risky:
                    if batch_reject:
                        self.conversation.append(ToolMessage(content="Action rejected by user.", tool_call_id=tool_call["id"], name=t_name))
                        continue
                        
                    if not batch_approve:
                        if on_tool_call:
                            u_choice = await on_tool_call(risky_msg)
                            if u_choice == 'all': batch_approve = True
                            elif u_choice == 'stop':
                                batch_reject = True
                                self.conversation.append(ToolMessage(content="Action rejected by user.", tool_call_id=tool_call["id"], name=t_name))
                                continue
                            elif u_choice != 'y':
                                self.conversation.append(ToolMessage(content="Action rejected by user.", tool_call_id=tool_call["id"], name=t_name))
                                continue
                        else:
                            # If no callback (e.g. headless API), we must reject for safety unless otherwise specified
                            self.conversation.append(ToolMessage(content="Action rejected: Human-in-the-loop confirmation required.", tool_call_id=tool_call["id"], name=t_name))
                            continue

                print(f"  {Colors.ACTION}[Executing] {t_name}({t_args}){Colors.RESET}")
                tool_target = next((t for t in master_toolset if getattr(t, 'name', None) == t_name), None)
                
                if tool_target:
                    try:
                        if inspect.iscoroutinefunction(getattr(tool_target, "func", None)) or inspect.iscoroutinefunction(tool_target.invoke):
                            tool_res = await tool_target.ainvoke(t_args)
                        else:
                            tool_res = tool_target.invoke(t_args)
                            
                        self.conversation.append(ToolMessage(content=str(tool_res), tool_call_id=tool_call["id"], name=t_name))
                    except Exception as exc:
                        self.conversation.append(ToolMessage(content=f"Error: {exc}", tool_call_id=tool_call["id"], name=t_name))
                else:
                    self.conversation.append(ToolMessage(content="Error: Unregistered tool.", tool_call_id=tool_call["id"], name=t_name))

# CLI Confirmation Helper
async def cli_confirm(risky_msg: str):
    prompt = f"\n{Colors.FAIL}{Colors.BOLD}[PROTECTION]{Colors.RESET} Allow Agent to {risky_msg}? (y/n/all/stop): "
    return input(prompt).strip().lower()

async def main():
    parser = argparse.ArgumentParser(description="Antigravity Conversational AI Matrix")
    parser.add_argument("--model", type=str, default="gemma4:latest", help="Local Ollama target configuration")
    args = parser.parse_args()
    
    print(f"\n{Colors.ACTION}=== SYSTEM ONLINE: AUTONOMOUS AGENT ({args.model}) ==={Colors.RESET}")
    session = AgentSession(model=args.model)
    
    while True:
        try:
            user_input = input(f"\n{Colors.YOU}You:{Colors.RESET} ").strip()
            if not user_input: continue
            if user_input.lower() in ['exit', 'quit']: break
            if user_input.lower() in ['help', '?', '/help']:
                print(f"\n{Colors.ACTION}=== HELP ==={Colors.RESET}")
                for t in master_toolset: print(f"  {t.name:25} : {t.description}")
                continue
                
            response = await session.run_turn(user_input, on_tool_call=cli_confirm)
            print(f"{Colors.ASSISTANT}Assistant:{Colors.RESET} {response}")
            
        except (KeyboardInterrupt, EOFError):
            break

if __name__ == "__main__":
    asyncio.run(main())