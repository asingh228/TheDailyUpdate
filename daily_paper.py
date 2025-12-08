import os
import re
import feedparser
from openai import OpenAI
from datetime import datetime

# --- CONFIGURATION ---
ARXIV_URL = 'http://export.arxiv.org/api/query?search_query=cat:cs.LG&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending'
# Cerebras uses an OpenAI-compatible endpoint
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
MODEL_ID = "llama3.1-8b"

def get_latest_paper():
    print(f"Fetching latest paper from: {ARXIV_URL}")
    data = feedparser.parse(ARXIV_URL)
    
    if not data.entries:
        raise ValueError("No papers found! Check ArXiv API status.")
        
    paper = data.entries[0]
    return {
        "title": paper.title,
        "abstract": paper.summary.replace("\n", " "),
        "link": paper.link
    }

def generate_summary(paper_title, paper_abstract):
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: CEREBRAS_API_KEY is missing from environment variables.")
        return "Error: API Key Missing"

    # We use the standard OpenAI client, but point it to Cerebras
    client = OpenAI(
        base_url=CEREBRAS_BASE_URL,
        api_key=api_key
    )

    prompt = (
        f"Summarize this AI paper into one punchy, technical sentence (max 40 words). "
        f"Focus on the architecture or novelty.\n\n"
        f"Title: {paper_title}\n"
        f"Abstract: {paper_abstract}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "You are a helpful AI researcher assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # PRINT THE ACTUAL ERROR so we can debug
        print(f"API CALL FAILED: {e}")
        return f"Summary unavailable (Error: {str(e)[:50]}...)"

def update_readme(paper_info, ai_summary):
    # Auto-detect filename
    if os.path.exists("README.md"):
        filename = "README.md"
    elif os.path.exists("readme.md"):
        filename = "readme.md"
    else:
        print("Error: README.md not found.")
        return

    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()

    start_marker = ""
    end_marker = ""
    
    # Validation: Ensure markers exist before trying to replace
    if start_marker not in content or end_marker not in content:
        print("ERROR: Markers not found in README.md. Please reset them.")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    
    new_entry = (
        f"{start_marker}\n"
        f"### ⚡ Daily ArXiv Pick ({date_str})\n"
        f"**[{paper_info['title']}]({paper_info['link']})**\n\n"
        f"> 🤖 **Llama-3.1 Summary:** {ai_summary}\n\n"
        f"{end_marker}"
    )

    # Regex: Replace everything between markers
    # re.DOTALL allows matching across newlines
    pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    updated_content = re.sub(pattern, new_entry, content, flags=re.DOTALL)

    with open(filename, "w", encoding="utf-8") as file:
        file.write(updated_content)
    print("README.md updated successfully.")

if __name__ == "__main__":
    try:
        paper = get_latest_paper()
        summary = generate_summary(paper['title'], paper['abstract'])
        update_readme(paper, summary)
    except Exception as e:
        print(f"Script crashed: {e}")
        exit(1)
