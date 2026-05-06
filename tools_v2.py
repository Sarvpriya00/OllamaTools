"""
tools_v2.py — Expanded Composable Tool Registry
================================================
14 MVP tools across 5 categories:
  Category 1: Core System Tools     (read_file, write_file, list_files, python_tool, bash_tool)
  Category 2: Web & Research Tools  (web_search, youtube_channel_scan, yt_dlp_tool)
  Category 3: Memory & Cache Tools  (cache_read, cache_write)
  Category 4: Script Gen Tools      (topic_analyzer, script_writer)
  Category 5: Orchestration Tools   (model_router, planner_tool)

Design Principle: Small, composable, single-responsibility tools.
Each tool does ONE thing well so the agent can chain them freely.
"""

import os
import json
import re
import ast
import hashlib
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────
# CATEGORY 1 — CORE SYSTEM TOOLS
# ─────────────────────────────────────────────────────────────

def read_file(path: str) -> str:
    """Read complete contents of a local file into context."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: '{path}' does not exist."
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading '{path}': {e}"


def write_file(path: str, content: str) -> str:
    """Create or overwrite a local file with string content."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Success: Wrote {len(content)} bytes to '{path}'."
    except Exception as e:
        return f"Error writing '{path}': {e}"


def list_files(directory: str = ".") -> str:
    """List all files and folders in a directory for project navigation."""
    try:
        d = Path(directory)
        if not d.exists():
            return f"Error: Directory '{directory}' does not exist."
        lines = []
        for item in sorted(d.iterdir()):
            kind = "DIR " if item.is_dir() else "FILE"
            size = f" ({item.stat().st_size}B)" if item.is_file() else ""
            lines.append(f"[{kind}] {item.name}{size}")
        return "\n".join(lines) if lines else "Directory is empty."
    except Exception as e:
        return f"Error listing '{directory}': {e}"


# Allowlisted built-ins only — no imports, no open(), no os, no sys
_PYTHON_BLOCKED = ["import", "open(", "os.", "sys.", "subprocess", "__", "exec(", "eval("]

def python_tool(code: str) -> str:
    """
    Run a safe Python snippet in a restricted sandbox.
    Use for: data analysis, CSV parsing, math calculations, JSON transforms.
    No imports, no file I/O, no system access. Pure logic only.
    """
    for banned in _PYTHON_BLOCKED:
        if banned in code:
            return f"Safety Block: '{banned}' is not allowed in python_tool. Use dedicated file/bash tools instead."
    try:
        # Capture stdout via exec into an isolated namespace
        import io, contextlib
        buf = io.StringIO()
        namespace = {"__builtins__": {"print": print, "len": len, "range": range,
                                       "int": int, "float": float, "str": str,
                                       "list": list, "dict": dict, "sum": sum,
                                       "min": min, "max": max, "abs": abs,
                                       "round": round, "sorted": sorted,
                                       "enumerate": enumerate, "zip": zip,
                                       "map": map, "filter": filter}}
        with contextlib.redirect_stdout(buf):
            exec(code, namespace)
        output = buf.getvalue()
        # Also capture last expression value if no print
        return output.strip() if output.strip() else "Success: Code executed with no output."
    except Exception as e:
        return f"Python Execution Error: {e}"


# Allowlisted commands for bash_tool
_BASH_ALLOWLIST = ["yt-dlp", "ffmpeg", "curl", "echo", "ls", "cat", "grep",
                   "wc", "head", "tail", "find", "du", "date", "pwd", "which",
                   "python3", "pip", "ffprobe", "mkdir"]

def bash_tool(command: str) -> str:
    """
    Execute a shell command from a strict allowlist only.
    Allowed commands: yt-dlp, ffmpeg, ffprobe, curl, echo, ls, cat, grep, wc,
    head, tail, find, du, date, pwd, which, python3, pip.
    Anything else is blocked for safety.
    """
    base_cmd = command.strip().split()[0] if command.strip() else ""
    if base_cmd not in _BASH_ALLOWLIST:
        return (f"Safety Block: '{base_cmd}' is not in the allowlist.\n"
                f"Allowed: {', '.join(_BASH_ALLOWLIST)}")
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if err and not out:
            return f"STDERR: {err}"
        return out if out else "Success: Command executed with no output."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Bash Error: {e}"


# ─────────────────────────────────────────────────────────────
# CATEGORY 2 — WEB & RESEARCH TOOLS
# ─────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web via DuckDuckGo and return ranked URLs with snippets.
    Use for: trends, news, research, competitor analysis.
    Returns structured text: Title, URL, Snippet for each result.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "Error: Search library not installed. Run: pip install ddgs"

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                if isinstance(r, dict) and r.get("href"):
                    results.append(
                        f"Title: {r.get('title', 'N/A')}\n"
                        f"URL: {r.get('href')}\n"
                        f"Snippet: {r.get('body', 'N/A')}"
                    )
        return "\n\n---\n\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search Error: {e}"


def youtube_channel_scan(channel_url: str, max_videos: int = 10) -> str:
    """
    Scan a YouTube channel and extract video metadata using yt-dlp.
    Returns: titles, view counts, upload dates, durations, video URLs.
    Use for: creator analysis, content strategy, trend spotting.
    """
    try:
        cmd = (
            f"yt-dlp --flat-playlist --dump-json "
            f"--playlist-end {max_videos} "
            f"'{channel_url}'"
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 and result.stderr:
            return f"yt-dlp Error: {result.stderr[:500]}"

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                videos.append({
                    "title": data.get("title", "N/A"),
                    "url": f"https://youtube.com/watch?v={data.get('id', '')}",
                    "duration": data.get("duration_string", data.get("duration", "N/A")),
                    "view_count": data.get("view_count", "N/A"),
                    "upload_date": data.get("upload_date", "N/A"),
                    "description": (data.get("description") or "")[:200],
                })
            except json.JSONDecodeError:
                continue

        if not videos:
            return "No videos found. Check the channel URL or yt-dlp version."

        lines = [f"Scanned {len(videos)} videos from: {channel_url}\n"]
        for i, v in enumerate(videos, 1):
            lines.append(
                f"{i}. {v['title']}\n"
                f"   URL: {v['url']}\n"
                f"   Duration: {v['duration']} | Views: {v['view_count']} | Date: {v['upload_date']}\n"
                f"   Desc: {v['description']}"
            )
        return "\n\n".join(lines)
    except subprocess.TimeoutExpired:
        return "Error: yt-dlp scan timed out after 120 seconds."
    except Exception as e:
        return f"Channel Scan Error: {e}"


def yt_dlp_tool(url: str, action: str = "metadata", output_dir: str = "./cache") -> str:
    """
    Download or extract data from a YouTube video using yt-dlp.
    Actions:
      - 'metadata'   → Returns full JSON metadata (title, description, tags, etc.)
      - 'subtitles'  → Downloads auto-generated subtitles as .vtt file
      - 'thumbnail'  → Downloads the best thumbnail image
      - 'audio'      → Downloads best audio as .mp3
    output_dir: local folder to save files to (created if missing).
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    action_map = {
        "metadata": f"yt-dlp --dump-json '{url}'",
        "subtitles": f"yt-dlp --write-auto-sub --skip-download --sub-format vtt -o '{output_dir}/%(id)s.%(ext)s' '{url}'",
        "thumbnail": f"yt-dlp --write-thumbnail --skip-download -o '{output_dir}/%(id)s.%(ext)s' '{url}'",
        "audio": f"yt-dlp -x --audio-format mp3 -o '{output_dir}/%(id)s.%(ext)s' '{url}'",
    }

    if action not in action_map:
        return f"Error: Unknown action '{action}'. Choose from: {list(action_map.keys())}"

    try:
        result = subprocess.run(
            action_map[action], shell=True, capture_output=True, text=True, timeout=300
        )
        if action == "metadata":
            # Parse and return structured metadata
            try:
                data = json.loads(result.stdout)
                return json.dumps({
                    "title": data.get("title"),
                    "channel": data.get("channel"),
                    "upload_date": data.get("upload_date"),
                    "duration": data.get("duration_string"),
                    "view_count": data.get("view_count"),
                    "like_count": data.get("like_count"),
                    "description": (data.get("description") or "")[:1000],
                    "tags": data.get("tags", [])[:20],
                    "categories": data.get("categories", []),
                }, indent=2)
            except json.JSONDecodeError:
                return result.stdout[:2000]

        err = result.stderr.strip()
        out = result.stdout.strip()
        if result.returncode == 0:
            return f"Success: '{action}' completed. Files saved to '{output_dir}'.\n{out[:500]}"
        return f"yt-dlp Error:\n{err[:1000]}"
    except subprocess.TimeoutExpired:
        return "Error: yt-dlp timed out after 300 seconds."
    except Exception as e:
        return f"yt_dlp_tool Error: {e}"


def find_image(query: str) -> str:
    """
    Search for an image using DuckDuckGo Image Search and return direct image URLs.
    Use this whenever the user asks to see an image, photo, or picture of anything.
    query: what to search for (e.g. 'MKBHD portrait photo', 'sunset wallpaper 4K')
    Returns: direct HTTPS image URLs ready for markdown embedding.
    The frontend will load and display these images directly.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "Error: Search library not installed. Run: pip install ddgs"

    # Check cache first
    cache_key = f"img:{query}"
    cache_path = Path("./cache")
    cache_path.mkdir(parents=True, exist_ok=True)
    cache_file = cache_path / f"{hashlib.md5(cache_key.encode()).hexdigest()}.json"
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            return cached.get("data", "Cache hit but no data.")
        except Exception:
            pass

    try:
        with DDGS() as ddgs:
            enhanced_query = f"{query} -site:unsplash.com -site:pinterest.com"
            results = list(ddgs.images(enhanced_query, max_results=10))
        if not results:
            return f"No images found for '{query}'."

        # Filter for valid HTTPS image URLs
        valid_images = []
        for r in results:
            img_url = r.get("image", "")
            if img_url.startswith("https://"):
                valid_images.append({
                    "url": img_url,
                    "title": r.get("title", ""),
                    "width": r.get("width", 0),
                    "height": r.get("height", 0),
                    "source": r.get("source", ""),
                })

        # Filter out unsplash placeholders and generic garbage
        reliable_images = [
            img for img in valid_images 
            if "unsplash.com" not in img["url"] and "placeholder" not in img["url"]
        ]
        
        # If we filtered everything, fallback to valid_images
        final_list = reliable_images if reliable_images else valid_images
        
        if not final_list:
            return "No reliable images found."

        # Pick the best (largest) from the reliable list
        best = max(final_list, key=lambda x: x.get("width", 0) * x.get("height", 0))
        best_url = best["url"]
        
        # Provide the best link and a backup link in the tool response
        response = f"![{query}]({best_url})"
        if len(final_list) > 1:
            backup_url = final_list[1]["url"]
            response += f"\n\n(Backup link: {backup_url})"

        # Cache the result
        try:
            cache_file.write_text(json.dumps({
                "key": cache_key,
                "timestamp": datetime.utcnow().isoformat(),
                "data": response
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

        return response
    except Exception as e:
        return f"Image Search Error: {e}"


# ─────────────────────────────────────────────────────────────
# CATEGORY 3 — MEMORY & CACHE TOOLS
# ─────────────────────────────────────────────────────────────

_CACHE_DIR = Path("./cache")

def _cache_key(key: str) -> Path:
    """Generate a stable file path from a cache key string."""
    safe = hashlib.md5(key.encode()).hexdigest()
    return _CACHE_DIR / f"{safe}.json"


def cache_write(key: str, data: str) -> str:
    """
    Save a value to the local disk cache under a string key.
    Use for: saving research results, metadata, transcripts to avoid re-fetching.
    Overwrites any existing value for the same key.
    """
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _cache_key(key)
        payload = {
            "key": key,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return f"Success: Cached '{key}' → {path.name}"
    except Exception as e:
        return f"Cache Write Error: {e}"


def cache_read(key: str) -> str:
    """
    Load a previously cached value by its string key.
    Returns the cached data string, or a miss message if not found.
    Always try cache_read before calling expensive web/yt-dlp tools.
    """
    try:
        path = _cache_key(key)
        if not path.exists():
            return f"Cache Miss: No cached data found for key '{key}'."
        payload = json.loads(path.read_text(encoding="utf-8"))
        age = payload.get("timestamp", "unknown")
        data = payload.get("data", "")
        return f"Cache Hit (saved at {age}):\n\n{data}"
    except Exception as e:
        return f"Cache Read Error: {e}"


# ─────────────────────────────────────────────────────────────
# CATEGORY 4 — SCRIPT GENERATION TOOLS
# ─────────────────────────────────────────────────────────────

def topic_analyzer(
    raw_content: str,
    content_type: str = "youtube"
) -> str:
    """
    Analyze raw research content and extract actionable creator intelligence.
    Identifies: trending subtopics, hook angles, audience pain points, content gaps.
    content_type: 'youtube', 'article', 'transcript', or 'search_results'
    raw_content: paste in scraped text, channel scan output, or search snippets.
    Returns a structured analysis markdown block.
    """
    if not raw_content or len(raw_content) < 50:
        return "Error: raw_content is too short. Provide at minimum a paragraph of context."

    # Build a structured prompt analysis without LLM (pure heuristic extraction)
    # The LLM in main.py will call this tool and then interpret the output itself
    word_count = len(raw_content.split())
    lines = [l.strip() for l in raw_content.split("\n") if l.strip()]

    # Extract potential title patterns (lines that look like video titles)
    title_candidates = [l for l in lines if 10 < len(l) < 120 and not l.startswith("{")][:15]

    # Detect high-frequency words (simple frequency analysis)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', raw_content.lower())
    freq: dict = {}
    for w in words:
        if w not in {"this", "that", "with", "from", "they", "have", "been",
                     "your", "will", "about", "what", "when", "then", "than",
                     "more", "some", "into", "just", "also", "like", "would"}:
            freq[w] = freq.get(w, 0) + 1
    top_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:20]

    analysis = (
        f"# Topic Analysis Report\n"
        f"**Content Type:** {content_type}\n"
        f"**Words Analyzed:** {word_count}\n\n"
        f"## Top Keywords / Themes\n"
        + "\n".join(f"- `{kw}` ({count}x)" for kw, count in top_keywords)
        + f"\n\n## Extracted Title Candidates\n"
        + "\n".join(f"- {t}" for t in title_candidates)
        + f"\n\n## Raw Content Preview\n```\n{raw_content[:800]}\n```\n"
        f"\n> Pass this analysis to script_planner or script_writer for the next step."
    )
    return analysis


def script_writer(
    topic: str,
    style: str = "educational",
    target_length: str = "medium",
    extra_context: str = ""
) -> str:
    """
    Generate a complete YouTube video script outline and draft.
    This tool produces a structured script template — the LLM fills it with content.
    style: 'educational', 'entertaining', 'documentary', 'shorts'
    target_length: 'short' (3-5 min), 'medium' (8-12 min), 'long' (15-20 min)
    extra_context: paste in topic_analyzer output or raw research to ground the script.

    Returns a complete script template in Markdown format.
    """
    length_map = {
        "short":  {"words": "400-600",  "sections": 4},
        "medium": {"words": "800-1200", "sections": 6},
        "long":   {"words": "1500-2500","sections": 8},
    }
    cfg = length_map.get(target_length, length_map["medium"])

    style_notes = {
        "educational": "Authoritative tone. Use analogies. Structure: Problem → Explanation → Solution.",
        "entertaining": "High-energy tone. Use humor and surprises. Structure: Hook → Story → Payoff.",
        "documentary": "Narrative tone. Use real data and quotes. Structure: Cold open → Context → Evidence → Conclusion.",
        "shorts": "Ultra-fast hook. First 3 seconds MUST hook. Structure: Hook → Single Point → CTA. Keep under 60 seconds.",
    }

    template = f"""# Script: {topic}

**Style:** {style} — {style_notes.get(style, '')}
**Target Length:** {target_length} ({cfg['words']} words)
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d')}

---

## HOOK (0:00 - 0:15)
> [Write a single sentence that immediately creates curiosity or states a bold claim]

**HOOK LINE:**
_[INSERT HOOK]_

---

## INTRO (0:15 - 0:45)
> [Establish who this is for and what they will learn. Do NOT over-explain.]

_[INSERT INTRO]_

---

## MAIN SECTIONS ({cfg['sections'] - 2} total)

### Section 1: [Key Point Name]
> [Supporting argument, example, or data point]
_[INSERT CONTENT]_

### Section 2: [Key Point Name]
> [Supporting argument, example, or data point]
_[INSERT CONTENT]_

### Section 3: [Key Point Name]
> [Supporting argument, example, or data point]
_[INSERT CONTENT]_

---

## CONCLUSION
> [Summarize the single most important takeaway]
_[INSERT CONCLUSION]_

---

## CALL TO ACTION
> [One clear action. Subscribe / Comment / Link in description.]
_[INSERT CTA]_

---

## RESEARCH CONTEXT
{extra_context[:1500] if extra_context else '_No additional context provided._'}

---
_Template generated by script_writer tool. Fill placeholders with LLM or manually._
"""
    return template


# ─────────────────────────────────────────────────────────────
# CATEGORY 5 — ORCHESTRATION TOOLS
# ─────────────────────────────────────────────────────────────

# Available local models and their best use cases
_MODEL_CAPABILITIES = {
    "gemma3:latest":      {"speed": "fast",   "strength": "chat, quick tasks, small prompts"},
    "gemma4:latest":      {"speed": "fast",   "strength": "chat, reasoning, tool calling"},
    "llama3:latest":      {"speed": "medium", "strength": "general purpose, instructions, writing"},
    "llama3.1:latest":    {"speed": "medium", "strength": "long context, analysis, research"},
    "mistral:latest":     {"speed": "fast",   "strength": "code, structured output, JSON"},
    "qwen2.5:latest":     {"speed": "medium", "strength": "coding, math, multilingual"},
    "deepseek-r1:latest": {"speed": "slow",   "strength": "complex reasoning, deep analysis"},
    "phi4:latest":        {"speed": "fast",   "strength": "small model, quick summaries"},
}

def model_router(task_description: str, priority: str = "balanced") -> str:
    """
    Recommend the best local Ollama model for a given task.
    priority: 'speed' (fastest model), 'quality' (best output), 'balanced' (default)

    Returns a JSON object with the recommended model and reasoning.
    Use this before any LLM-heavy operation to pick the optimal model.
    """
    task_lower = task_description.lower()

    # Heuristic routing rules
    if any(w in task_lower for w in ["code", "python", "javascript", "debug", "json", "script"]):
        recommended = "mistral:latest" if priority == "speed" else "qwen2.5:latest"
        reason = "Coding/structured output task detected."
    elif any(w in task_lower for w in ["reason", "analyze", "deep", "complex", "research"]):
        recommended = "llama3.1:latest" if priority != "speed" else "gemma4:latest"
        reason = "Deep reasoning/analysis task detected."
    elif any(w in task_lower for w in ["write", "script", "story", "essay", "creative"]):
        recommended = "llama3:latest" if priority != "speed" else "gemma4:latest"
        reason = "Writing/creative task detected."
    elif any(w in task_lower for w in ["summarize", "summary", "brief", "short", "quick"]):
        recommended = "phi4:latest" if priority == "speed" else "gemma4:latest"
        reason = "Summarization task — lightweight model preferred."
    elif any(w in task_lower for w in ["math", "calculate", "number", "formula"]):
        recommended = "qwen2.5:latest"
        reason = "Mathematical reasoning task detected."
    else:
        recommended = "gemma4:latest"
        reason = "General task — default model selected."

    caps = _MODEL_CAPABILITIES.get(recommended, {})
    return json.dumps({
        "recommended_model": recommended,
        "reasoning": reason,
        "speed": caps.get("speed", "unknown"),
        "best_for": caps.get("strength", "unknown"),
        "priority_mode": priority,
        "all_available_models": list(_MODEL_CAPABILITIES.keys()),
    }, indent=2)


def planner_tool(goal: str, available_tools: Optional[str] = None) -> str:
    """
    Generate a step-by-step execution plan for a complex goal.
    Breaks the goal into a sequence of small, composable tool calls.
    available_tools: optionally pass a comma-separated list of tool names to constrain the plan.

    Returns a numbered execution plan in Markdown with tool call suggestions.
    """
    if not goal or len(goal) < 10:
        return "Error: Goal is too vague. Provide a specific objective."

    tools_note = ""
    if available_tools:
        tools_note = f"\n**Constrained to tools:** {available_tools}"

    # Generate a structured plan scaffold
    plan = f"""# Execution Plan
**Goal:** {goal}
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}{tools_note}

---

## Pre-flight Checks
- [ ] Step 0: `cache_read("{goal[:40]}")` — Check if this goal was already researched.

## Phase 1 — Research & Discovery
- [ ] Step 1: `web_search("{goal}")` — Get initial context and relevant URLs.
- [ ] Step 2: _(If YouTube-related)_ `youtube_channel_scan("<channel_url>")` — Extract video metadata.
- [ ] Step 3: `cache_write("{goal[:40]}", <search_results>)` — Cache raw results.

## Phase 2 — Analysis
- [ ] Step 4: `topic_analyzer(<cached_content>)` — Extract themes, keywords, hook angles.
- [ ] Step 5: `model_router("{goal}")` — Select optimal LLM for the next generation step.

## Phase 3 — Generation
- [ ] Step 6: `script_writer("{goal}", style="educational", extra_context=<analysis>)` — Draft script.
- [ ] Step 7: `write_file("output/{goal[:20].replace(' ', '_')}_script.md", <script>)` — Save output.

## Phase 4 — Verification
- [ ] Step 8: `read_file("output/{goal[:20].replace(' ', '_')}_script.md")` — Verify saved content.

---

> **Note:** This is a scaffold. The agent should adapt steps based on tool outputs.
> Skip steps that are not applicable. Add steps for any yt-dlp downloads if needed.
"""
    return plan


# ─────────────────────────────────────────────────────────────
# TOOL REGISTRY — Maps string names to callables
# ─────────────────────────────────────────────────────────────

TOOL_REGISTRY_V2 = {
    # Category 1 — Core System
    "read_file":             read_file,
    "write_file":            write_file,
    "list_files":            list_files,
    "python_tool":           python_tool,
    "bash_tool":             bash_tool,
    # Category 2 — Web & Research
    "web_search":            web_search,
    "youtube_channel_scan":  youtube_channel_scan,
    "yt_dlp_tool":           yt_dlp_tool,
    "download_image":        find_image,  # alias for backward compat
    "find_image":            find_image,
    # Category 3 — Memory & Cache
    "cache_read":            cache_read,
    "cache_write":           cache_write,
    # Category 4 — Script Generation
    "topic_analyzer":        topic_analyzer,
    "script_writer":         script_writer,
    # Category 5 — Orchestration
    "model_router":          model_router,
    "planner_tool":          planner_tool,
}
