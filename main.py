import argparse
import asyncio
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from crawl4ai import AsyncWebCrawler

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

# Import the existing tool registry bridges
import tools as sys_tools

# ==========================================
# 1. ContentFilter Class
# ==========================================
class ContentFilter:
    @staticmethod
    def filter_html(html_content: str, bypass: bool = False) -> str:
        """Uses Regex and BeautifulSoup to strip noise unless bypassed."""
        soup = BeautifulSoup(html_content, "lxml")

        if bypass:
            return soup.get_text(separator='\n', strip=True)[:10000]

        # Decompose non-content elements
        tags_to_decompose = ['nav', 'header', 'footer', 'aside', 'img', 'video', 'iframe', 'script', 'style', 'canvas', 'svg']
        for tag in soup(tags_to_decompose):
            tag.decompose()

        # Regex stripping for promotional classes/IDs
        spam_pattern = re.compile(r'ad|banner|promo|sponsor|newsletter|popup|sidebar', re.IGNORECASE)
        for tag in soup.find_all(True):
            classes = tag.get('class', [])
            tag_id = tag.get('id', '')
            class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)
            if spam_pattern.search(class_str) or spam_pattern.search(str(tag_id)):
                tag.decompose()

        # Isolate semantic text cleanly
        clean_text = soup.get_text(separator='\n', strip=True)
        # Normalize structural whitespace
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        
        # Max context truncation (128K context supports longer logic, but maps process individually)
        return clean_text[:12000]

# ==========================================
# 2. Tool Bindings (Functional Python triggers)
# ==========================================

@tool
def read_file(path: str) -> str:
    """Read the complete contents of a file."""
    return sys_tools.read_file(path)

@tool
def write_file(path: str, content: str) -> str:
    """Create a new file or overwrite an existing file with content."""
    return sys_tools.write_file(path, content)

@tool
def edit_file(path: str, find: str, replace: str) -> str:
    """Find and replace a specific string within a file."""
    return sys_tools.edit_file(path, find, replace)

@tool
def list_files(directory: str) -> str:
    """List files and directories in the specified directory."""
    return sys_tools.list_files(directory)

@tool
def create_directory(path: str) -> str:
    """Create a new directory."""
    return sys_tools.create_directory(path)

@tool
def rename_file(old_path: str, new_path: str) -> str:
    """Rename or move a file or directory."""
    return sys_tools.rename_file(old_path, new_path)

@tool
def delete_file(path: str) -> str:
    """Delete a file or directory. REQUIRES APPROVAL."""
    return sys_tools.delete_file(path, approved=True)

@tool
def search_in_files(directory: str, query: str) -> str:
    """Search for a text query within all files in a directory."""
    return sys_tools.search_in_files(directory, query)

@tool
def run_bash(command: str) -> str:
    """Execute a bash command. Executing in a safe subprocess."""
    return sys_tools.run_bash(command, approved=True)

@tool
def download_file(url: str, path: str) -> str:
    """Download a file from an internet URL to a local path."""
    return sys_tools.download_file(url, path, approved=True)

@tool
def parse_json(text: str) -> str:
    """Parse a JSON string to ensure valid structure and format it."""
    return sys_tools.parse_json(text)

@tool
def web_search(query: str, max_results: int = 3) -> str:
    """Perform a web search using DuckDuckGo to return relevant URLs."""
    urls = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            for r in results:
                if r.get('href'):
                    urls.append(r['href'])
        return "\n".join(urls)
    except Exception as e:
        return f"Web search error: {e}"


async def perform_fetch_url(url: str, bypass_filter: bool = False) -> str:
    """Asynchronous scrape using Crawl4AI to bypass blocking threads."""
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, bypass_cache=True)
            if result.success and result.html:
                return ContentFilter.filter_html(result.html, bypass=bypass_filter)
            return f"Extract Error: Unable to fetch {url}"
    except Exception as e:
        return f"System Error scraping {url}: {str(e)}"

@tool
async def fetch_url(url: str) -> str:
    """Fetch and return Markdown content of a URL."""
    return await perform_fetch_url(url, bypass_filter=False)

# Collect all tools to bind into the agent phase
all_agent_tools = [
    read_file, write_file, edit_file, list_files, create_directory,
    rename_file, delete_file, search_in_files, run_bash, download_file,
    parse_json, web_search, fetch_url
]

# ==========================================
# 3. Model Bridge & Deep Research Workflow
# ==========================================

async def main():
    # 1. Interface & Configuration implementation
    parser = argparse.ArgumentParser(description="Multi-Agent System Restore: Antigravity Architecture")
    parser.add_argument("--model", type=str, default="gemma4:latest", help="Local Ollama model identifier")
    args = parser.parse_args()
    
    print("\n=== SYSTEM ONLINE: ANTIGRAVITY RESEARCH ===")
    print(f"[*] Core Engine: {args.model}")
    print("[*] Status: Ready\n")
    
    goal = input("Research Objective: ").strip()
    if not goal:
         print("Validation Error: Objective required.")
         return
         
    # Intercept bypass keywords natively per parameters
    bypass_filter = any(kw in goal.lower() for kw in ["raw", "full source", "exact website text", "unfiltered"])
    if bypass_filter:
        print("[!] ContentFilter Bypass Protocol Authorized. Proceeding with raw extraction.")
        
    # Configure the Langchain Ollama Bridge enforcing large context
    llm = ChatOllama(
        model=args.model,
        base_url="http://localhost:11434",
        temperature=0,
        num_ctx=128000
    )
    
    # [PHASE 1: PLAN]
    print("\n[Phase 1/5] Architectural Planning...")
    plan_prompt = PromptTemplate.from_template(
        "You are an elite research AI. Decompose this research goal into exactly 3 to 5 highly specific DuckDuckGo search queries.\n"
        "Output ONLY the queries, one per line. No introduction, no numbers, and no bullets.\n\n"
        "Goal: {goal}"
    )
    try:
        plan_res = llm.invoke(plan_prompt.format(goal=goal))
        queries = [q.strip() for q in plan_res.content.split('\n') if q.strip()][:5]
        for q in queries: 
            print(f"  -> {q}")
    except Exception as e:
        print(f"Planning Fault: Failed to reach Ollama model. Ensure {args.model} is installed.\nDetails: {e}")
        return
        
    if not queries:
        return
        
    # [PHASE 2: EXECUTE]
    print("\n[Phase 2/5] Parallel Execution (Eyes & Hands)...")
    all_urls = set()
    for q in queries:
         try:
             # Using the underlying tool directly in the pipeline code to guarantee performance
             res_string = web_search.invoke({"query": q, "max_results": 2})
             urls = [u.strip() for u in res_string.split('\n') if u.strip().startswith('http')]
             all_urls.update(urls)
         except Exception as e:
             print(f"  [-] Search error resolving '{q}': {e}")
             
    target_urls = list(all_urls)[:5] # Enforce strict cap for testing
    print(f"  * Locating {len(target_urls)} distinct prime endpoints.")

    print("\n[Phase 3/5] Extracting & Filtering Data...")
    fetch_tasks = [perform_fetch_url(u, bypass_filter) for u in target_urls]
    raw_contents = await asyncio.gather(*fetch_tasks)
    
    valid_contents = []
    for u, txt in zip(target_urls, raw_contents):
        # Validate that the string response is not exceptionally short or containing basic fail texts
        if len(txt) > 50 and not txt.startswith("Extract Error") and not txt.startswith("System Error"):
            valid_contents.append((u, txt))
    print(f"  * Yielded {len(valid_contents)} valid structural documents.")
    
    if not valid_contents:
        print("Data Exhausted: No active contents scraped. Exiting cycle.")
        return

    # [PHASE 3: SUMMARIZE (MAP MODE)]
    print("\n[Phase 4/5] Contextual Mapping (Granular Summarization)...")
    map_prompt = PromptTemplate.from_template(
        "Execute a dense, highly technical summary of the provided raw data. "
        "Focus entirely on vectors, factual statistics, and actionable intelligence. "
        "Discard redundant narrative filler. Keep within 500 words.\n\n"
        "Raw Data Context:\n{text}\n\nTechnical Synthesis:"
    )
    
    summaries = []
    for i, (source_url, text) in enumerate(valid_contents):
        try:
             print(f"  -> Trimming cognitive data matrix {i+1}...")
             res = llm.invoke(map_prompt.format(text=text))
             summaries.append(f"SOURCE_URL: {source_url}\n\nARTICLE_SUMMARY:\n{res.content}")
        except Exception as e:
             print(f"  [-] Inference error on node {i+1}: {e}")
             
    if not summaries:
        print("Mapping Protocol Failed. Exiting.")
        return
        
    # [PHASE 4: SAVE (REDUCE via TOOL AGENT)]
    print("\n[Phase 5/5] Autonomous Agents: Synthesis and Local Write Protocol...")
    
    # Tool Binding injection natively available via LangChain implementation
    llm_with_tools = llm.bind_tools(all_agent_tools)
    
    compiled_knowledge = "\n\n" + "="*50 + "\n\n".join(summaries)
    
    agent_instructions = (
        "You are an autonomous administrative and research intelligence matrix.\n"
        "Your priority target is to analyze the preceding Map-Reduced summaries and generate individual markdown files for each.\n"
        f"Goal: {goal}\n\n"
        "STRICT EXECUTION DIRECTIVES:\n"
        "1. For EACH distinct article summary I have provided below, YOU MUST trigger the 'write_file' tool to save that summary onto the local disk as an individual '.md' file (e.g., 'topic_insight_1.md', 'breakthrough_research_2.md'). Do not skip any documents.\n"
        "2. Do NOT lump summaries into a single file. Each source logically deserves its own isolated path.\n"
        "3. Wait to receive execution confirmation from each 'write_file' response.\n"
        "4. Once all files have been safely encoded on disk, communicate a final status utilizing the minimalist, benefit-oriented syntax defined by the Apple Style Guide standard.\n"
        "DO NOT assume data is saved, prove it via functional tool execution.\n\n"
        f"AWAITING PROCESS ON THESE SUMMARIES:\n{compiled_knowledge}"
    )

    messages = [
        {"role": "system", "content": "You possess local administrative execution powers via explicit tools."},
        {"role": "user", "content": agent_instructions}
    ]
    
    # Lightweight Custom Agent Loop explicitly tracking calls, errors, and traces
    max_steps = 15
    for step in range(max_steps):
        try:
             ai_msg = llm_with_tools.invoke(messages)
             messages.append(ai_msg)
             
             # If the LLM doesn't request a tool execution, we assume it's delivering its final text synthesis
             if not getattr(ai_msg, "tool_calls", None):
                  print("\n=== FINAL EXECUTIVE REPORT ===")
                  print(ai_msg.content)
                  break
                  
             # Intercept explicitly bound tool calls
             for tool_call in ai_msg.tool_calls:
                  t_name = tool_call.get("name")
                  t_args = tool_call.get("args", {})
                  
                  print(f"  [Agent Executing Tool] -> {t_name}({t_args})")
                  
                  tool_target = next((t for t in all_agent_tools if getattr(t, 'name', None) == t_name), None)
                  if tool_target:
                      try:
                          tool_result = tool_target.invoke(t_args)
                          # Return tool results into the immediate chat history
                          messages.append({
                              "role": "tool",
                              "tool_call_id": tool_call["id"],
                              "name": t_name,
                              "content": str(tool_result)
                          })
                      except Exception as te:
                          # Inject Python-layer errors directly into context for automatic Agent correction
                          messages.append({
                              "role": "tool",
                              "tool_call_id": tool_call["id"],
                              "name": t_name,
                              "content": f"Execution Error: {te}"
                          })
                  else:
                      messages.append({
                          "role": "tool",
                          "tool_call_id": tool_call["id"],
                          "name": t_name,
                          "content": "Framework Error: Tool referenced is unavailable in registry."
                      })
                      
        except Exception as e:
             print(f"\n[!] Mission Critical Agent Fault trace: {e}")
             break

if __name__ == "__main__":
    asyncio.run(main())