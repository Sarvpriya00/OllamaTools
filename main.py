import argparse
import asyncio
import re
import warnings
import inspect
from typing import List, Optional
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# Use updated ddgs library (replaces deprecated duckduckgo_search)
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# Muffle verbose system warnings to preserve terminal UI UX
warnings.simplefilter("ignore", ResourceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

# Legacy tool registry (Category 0 — original tools)
import tools as sys_tools
# Expanded composable tool registry (Categories 1-5)
import tools_v2 as v2

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
            results = ddgs.text(query, max_results=max_results)
            if results:
                for r in results:
                    if isinstance(r, dict) and r.get('href'):
                        urls.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nDesc: {r.get('body')}")
        return "\n\n".join(urls) if urls else "No results found."
    except Exception as e:
        return f"Web search error: {e}"


# ==========================================
# NEW TOOLS — Wrapped from tools_v2.py
# ==========================================

@tool
def read_file(path: str) -> str:
    """Read the complete contents of a local file into the agent's context."""
    return v2.read_file(path)

@tool
def write_file(path: str, content: str) -> str:
    """Create a new file or overwrite an existing file with string content. Automatically creates parent directories."""
    return v2.write_file(path, content)

@tool
def list_files(directory: str = ".") -> str:
    """List all files and subdirectories inside a directory for project navigation."""
    return v2.list_files(directory)

@tool
def python_tool(code: str) -> str:
    """
    Execute a safe Python snippet in a sandboxed environment.
    Use for: math calculations, data analysis, JSON transforms, CSV parsing.
    No imports, no file I/O, no system access allowed — pure logic only.
    """
    return v2.python_tool(code)

@tool
def bash_tool(command: str) -> str:
    """
    Execute a shell command from a strict allowlist.
    Allowed: yt-dlp, ffmpeg, ffprobe, curl, echo, ls, cat, grep, wc, head, tail, find, du, date, pwd, which, python3, pip.
    All other commands are blocked for safety.
    """
    return v2.bash_tool(command)

@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web via DuckDuckGo and return ranked results with titles, URLs, and snippets.
    Use for: trends, news, research, competitor analysis.
    """
    return v2.web_search(query, max_results)

@tool
def youtube_channel_scan(channel_url: str, max_videos: int = 10) -> str:
    """
    Scan a YouTube channel and extract video metadata: titles, views, upload dates, durations.
    Use for: creator analysis, content strategy, trend spotting.
    Requires yt-dlp to be installed.
    """
    return v2.youtube_channel_scan(channel_url, max_videos)

@tool
def yt_dlp_tool(url: str, action: str = "metadata", output_dir: str = "./cache") -> str:
    """
    Download or extract data from a YouTube video using yt-dlp.
    action options:
      'metadata'  → Returns full JSON metadata (title, description, tags, etc.)
      'subtitles' → Downloads auto-generated subtitles as .vtt file
      'thumbnail' → Downloads the best quality thumbnail image
      'audio'     → Downloads best audio as .mp3
    output_dir: local directory to save files (created automatically if missing).
    """
    return v2.yt_dlp_tool(url, action, output_dir)

@tool
def cache_read(key: str) -> str:
    """
    Load a previously saved value from the local disk cache by string key.
    Always try this BEFORE calling expensive web or yt-dlp tools to avoid redundant work.
    Returns the cached data or a miss message.
    """
    return v2.cache_read(key)

@tool
def cache_write(key: str, data: str) -> str:
    """
    Save a value to the local disk cache under a string key.
    Use after any expensive fetch (web search, channel scan, yt-dlp) to avoid re-fetching.
    """
    return v2.cache_write(key, data)

@tool
def topic_analyzer(raw_content: str, content_type: str = "youtube") -> str:
    """
    Analyze raw research content and extract creator intelligence.
    Identifies: trending subtopics, hook angles, audience pain points, keyword frequency.
    content_type: 'youtube', 'article', 'transcript', or 'search_results'
    Returns a structured Markdown analysis block ready for script planning.
    """
    return v2.topic_analyzer(raw_content, content_type)

@tool
def script_writer(topic: str, style: str = "educational", target_length: str = "medium", extra_context: str = "") -> str:
    """
    Generate a complete YouTube video script template.
    style: 'educational', 'entertaining', 'documentary', 'shorts'
    target_length: 'short' (3-5 min), 'medium' (8-12 min), 'long' (15-20 min)
    extra_context: paste in topic_analyzer output or research to ground the script.
    Returns a structured Markdown script with fillable sections.
    """
    return v2.script_writer(topic, style, target_length, extra_context)

@tool
def model_router(task_description: str, priority: str = "balanced") -> str:
    """
    Recommend the best local Ollama model for a given task.
    priority: 'speed' (fastest), 'quality' (best output), 'balanced' (default)
    Returns a JSON object with the recommended model name and reasoning.
    Always call this before any heavy LLM generation step.
    """
    return v2.model_router(task_description, priority)

@tool
def planner_tool(goal: str, available_tools: str = "") -> str:
    """
    Generate a step-by-step execution plan for a complex multi-step goal.
    Breaks the goal into a sequence of small, composable tool calls with checkboxes.
    available_tools: optionally pass comma-separated tool names to constrain the plan.
    Returns a numbered Markdown plan with suggested tool calls at each step.
    """
    return v2.planner_tool(goal, available_tools or None)

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

# Aggregate Agent Tools — Full 14-tool MVP + legacy tools
master_toolset = [
    # Category 1 — Core System (NEW)
    read_file, write_file, list_files, python_tool, bash_tool,
    # Category 2 — Web & Research (NEW)
    web_search, youtube_channel_scan, yt_dlp_tool,
    # Category 3 — Memory & Cache (NEW)
    cache_read, cache_write,
    # Category 4 — Script Generation (NEW)
    topic_analyzer, script_writer,
    # Category 5 — Orchestration (NEW)
    model_router, planner_tool,
    # Legacy tools (kept for backwards compatibility)
    edit_file, create_directory, rename_file, delete_file,
    search_in_files, run_bash, parse_json,
    standard_web_search, perform_deep_research,
]

# ==========================================
# 3. AgentSession (Stateful Controller)
# ==========================================

class AgentSession:
    def __init__(self, model: str):
        self.model = model
        self.core_engine = ChatOllama(model=model, base_url="http://localhost:11434", temperature=0, num_ctx=128000)
        self.agent_engine = self.core_engine.bind_tools(master_toolset)
        # Wire core_engine for deep research map-reduce
        global core_engine
        core_engine = self.core_engine
        self.conversation = [
            SystemMessage(content=(
                "# Sentry Agent — System Identity\n\n"
                "You are Sentry, a high-performance autonomous AI assistant specialized in "
                "content creation intelligence, deep research, and file system operations.\n\n"

                "## IDENTITY\n"
                "- Name: Sentry\n"
                "- Personality: Sharp, precise, visually-driven. Never verbose. Never filler.\n"
                "- Tone: Professional, direct, confident. Follow the Apple Style Guide at all times.\n\n"

                "## OUTPUT FORMAT — ALWAYS FOLLOW\n"
                "- Use clean structured Markdown in all responses.\n"
                "- Use ### for section headers, --- for separators.\n"
                "- Use **bold** for key terms, `backticks` for tool names and file paths.\n"
                "- For lists of steps or facts: use numbered lists.\n"
                "- For any code output: wrap in triple-backtick code blocks with language tag.\n"
                "- End complex responses with a '### Next Steps' section suggesting the next tool call.\n\n"

                "## TOOL PHILOSOPHY — COMPOSABLE PIPELINES ONLY\n"
                "Never build a mega-tool. Always chain small tools.\n"
                "Canonical pipelines:\n"
                "  - Research:  `web_search` → `topic_analyzer` → `write_file`\n"
                "  - YouTube:   `youtube_channel_scan` → `cache_write` → `topic_analyzer` → `script_writer`\n"
                "  - Video DL:  `cache_read` → `yt_dlp_tool` → `cache_write`\n"
                "  - Any Goal:  `planner_tool` → execute each step → `write_file` (save output)\n\n"

                "## EXECUTION RULES — READ CAREFULLY\n"
                "1. NEVER stop research after a single `web_search`. That is incomplete.\n"
                "   Run `web_search` 2-3 times with DIFFERENT query angles to gather broad data.\n"
                "2. NEVER say 'the search results point to directories' or 'I found some websites'.\n"
                "   These are NOT answers. Extract ACTUAL NAMES, FACTS, and DATA from those sources.\n"
                "3. If the user asks 'find me X' or 'who is the best Y' — you MUST return a NAMED LIST.\n"
                "   Not website suggestions. Real creator/person/product names with context.\n"
                "4. For ANY complex goal: call `planner_tool` FIRST. Never skip this.\n"
                "5. Before ANY expensive network call: call `cache_read` to avoid re-fetching.\n"
                "6. After ANY expensive fetch: call `cache_write` immediately to persist results.\n"
                "7. Before ANY heavy generation task: call `model_router` to pick the optimal model.\n"
                "8. If the user asks for a script: always call `topic_analyzer` on research first.\n\n"

                "## WHAT GOOD OUTPUT LOOKS LIKE\n"
                "BAD: 'The search results indicate that collabstr.com lists NYC influencers.'\n"
                "GOOD:\n"
                "### Top NYC YouTubers\n"
                "1. **Casey Neistat** — cinematic NYC vlogs, 12M subs.\n"
                "2. **NY Times Cooking** — food content, 800K subs.\n"
                "3. **SomeOrdinaryGamers** — gaming/commentary, 3.5M subs.\n\n"
                "Always return REAL NAMES, subscriber counts, niche, and why they fit the request.\n\n"

                "## IMAGE DISPLAY — YOU CAN AND MUST DISPLAY IMAGES\n"
                "You ARE capable of displaying images. The frontend renders markdown images natively.\n"
                "DO NOT ever say 'I cannot display images'. That is FALSE.\n\n"
                "When the user asks to see an image/photo/picture:\n"
                "1. Call `find_image` with a descriptive search query.\n"
                "2. The tool returns a direct HTTPS image URL and a markdown line.\n"
                "3. Copy the ![alt](url) line EXACTLY into your response text.\n"
                "4. The frontend will load and display the image directly from the internet.\n"
                "5. Results are cached — repeat queries are instant.\n\n"
                "NEVER refuse. NEVER say you cannot display images. Just call `find_image`.\n\n"

                "## SAFETY RULES\n"
                "- `bash_tool` executes from a strict allowlist only: yt-dlp, ffmpeg, ffprobe, curl, grep, ls, find, echo, wc, head, tail, du, date, which, python3, pip.\n"
                "- `python_tool` is sandboxed: no imports, no file I/O, no system access — pure logic only.\n"
                "- `delete_file` and `run_bash` with dangerous commands ALWAYS require explicit user approval.\n\n"

                "## RESPONSE STYLE\n"
                "- Never say 'I'll help you with that.' Just do it.\n"
                "- Never say 'As an AI language model'. Never apologize. Never pad.\n"
                "- Never end with 'Would you like me to...' — just execute the logical next step.\n"
                "- If you are running tools, briefly state which tool you are calling and why.\n"
                "- If a task is done, summarize the output in a structured Markdown block.\n"
                "- If you save a script or long text to a file using `write_file`, you MUST ALSO include the FULL content of that file (or a very detailed summary) in your response text so the user can see it immediately.\n"
                "- If results were saved to a file, always confirm the file path at the end."
            ))
        ]

    async def run_turn(self, user_input: str, on_tool_call=None):
        """Processes one turn of the conversation, handling recursive tool calls."""
        self.conversation.append(HumanMessage(content=user_input))
        
        # Turn-level batch approval tracking
        batch_approve = False
        batch_reject = False
        
        MAX_TOOL_ROUNDS = 15
        tool_round = 0
        call_history = []  # Track (name, args_hash) to detect loops
        
        while True:
            tool_round += 1
            if tool_round > MAX_TOOL_ROUNDS:
                return "⚠️ Reached maximum tool execution rounds. Here is what I have so far based on the tools executed above."
            try:
                ai_msg = self.agent_engine.invoke(self.conversation)
            except Exception as e:
                print(f"{Colors.FAIL}Engine Fault: {e}{Colors.RESET}")
                return f"System Error: {e}"
                
            self.conversation.append(ai_msg)
            
            if not getattr(ai_msg, "tool_calls", None):
                if not ai_msg.content.strip():
                    # Force a summary if the model was silent
                    self.conversation.append(HumanMessage(content="Task complete. Please provide a detailed final summary of your work and display any content you generated (scripts, findings, etc.) directly here."))
                    ai_msg = self.agent_engine.invoke(self.conversation)
                    self.conversation.append(ai_msg)
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
                
                # Detect duplicate tool calls (same tool + same args)
                import hashlib as _hl
                args_sig = (t_name, _hl.md5(str(sorted(t_args.items())).encode()).hexdigest())
                call_history.append(args_sig)
                dup_count = call_history.count(args_sig)
                if dup_count >= 3:
                    print(f"  {Colors.FAIL}[LOOP DETECTED] Redirecting to final response.{Colors.RESET}")
                    # Instead of continuing, we'll tell the agent to stop in the next round
                    self.conversation.append(ToolMessage(
                        content=f"STOP: You have called {t_name} with these arguments {dup_count} times. You MUST now provide a final answer to the user using the information you already have. DO NOT call any more tools.",
                        tool_call_id=tool_call["id"], name=t_name
                    ))
                    # Force a final generation and break the while loop
                    final_msg = self.agent_engine.invoke(self.conversation)
                    self.conversation.append(final_msg)
                    return final_msg.content
                
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

            # --- POST-TOOL CHECK ---
            # If we just processed tool calls, we loop back to invoke the model again.
            # However, some models might return empty content along with tool calls.
            # We want to make sure the FINAL message is never empty.
            # The next round of self.agent_engine.invoke(self.conversation) will happen at the top of the while loop.
        
        # This part should technically not be reachable because the loop returns from inside if tool_calls is empty.
        return "Internal Error: Conversation flow broken."

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