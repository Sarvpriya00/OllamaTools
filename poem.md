

System Prompt: "I want to build a Python-based Deep Research Agent using Ollama (running Llama 3 or Mistral) as the local reasoning engine. The agent must follow a 'Multi-Step Thinking' logic.

The workflow must include:

Query Decomposition: Take a user topic and generate 3-5 distinct search queries.

Browsing Layer: Use a Python tool to fetch live web results.

Information Extraction: For each URL, scrape the text and use a small Ollama model to summarize only the parts relevant to the query.

Recursive Gap Analysis: The agent should check its findings and generate one 'follow-up' search if information is missing.

Final Synthesis: Compile all summaries into a structured Markdown report with a 'Technical Analysis' and 'Executive Summary' section.

Please provide the Python structure using an Agentic framework, and explain how to handle the context window limitations of local LLMs."

2. The Recommended Python Stack
To make this work locally with Ollama, you’ll need these specific libraries:

A. The Orchestrator (The Brain)
LangChain or CrewAI: These are the "glue" libraries. They allow you to define "Agents" and "Tools."

Why: They have built-in support for Ollama through the OllamaLLM class.

B. The Search Engine (The Eyes)
DuckDuckGo Search (DDGS): As we used earlier, it's free and requires no API key.

Tavily API (Optional): If you want "Pro" results, Tavily is a search engine specifically optimized for AI agents (it filters out SEO spam).

C. The Scraper (The Hands)
Crawl4AI or Firecrawl: These are new, high-performance libraries designed specifically to turn websites into clean Markdown for LLMs. They are much better than raw BeautifulSoup for deep research.

D. The Local Model (Ollama)
Model Recommendation: Use Llama 3 (8B) or Mistral.

Command: ollama run llama3


what should be the workflow for our app

main.py take the user system prompt 
ollama llm should break down the prompt figure out which tools is to be used , fo rthe section it needs to google search or scrape the internet the llm first breaks the search query and figure out what needs to be search exactly what the user wants to know. then create multiple parralel searches each with diffrent variations of the search query, now after the search is done then scrape those sites. pass them to a python tool that filters out the promotional words and advertisements, images and videos, once the filtering is done then only the ai reads the file and then figureout what needs to be done filtering should be on by default but if the user mentions it needs the content exactly from the website then filtering should be bypassed 