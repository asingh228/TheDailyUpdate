import os
import re
import feedparser
from cerebras.cloud.sdk import Cerebras
from datetime import datetime

# --- CONFIGURATION ---
ARXIV_URL = 'http://export.arxiv.org/api/query?search_query=cat:cs.LG&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending'
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
    # 1. Initialize Cerebras Client
    # It automatically looks for CEREBRAS_API_KEY in env vars
    if not os.environ.get("CEREBRAS_API_KEY"):
         raise ValueError("CEREBRAS_API_KEY not found in environment variables.")

    client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

    prompt = (
        f"Summarize this AI paper into one punchy, technical sentence (max 40 words) for a GitHub profile. "
        f"Focus on the architecture or novelty.\n\n"
        f"Title: {paper_title}\n"
        f"Abstract: {paper_abstract}"
    )

    try:
        # 2. Call Llama 3.1-8b
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
        print(f"Error calling Cerebras: {e}")
        return "Summary unavailable (API Error)."

def update_readme(paper_info, ai_summary):
    filename = "README.md"
    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()

    start_marker = ""
    end_marker = ""
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Simple Markdown structure
    new_entry = (
        f"{start_marker}\n"
        f"### ⚡ Daily ArXiv Pick ({date_str})\n"
        f"**[{paper_info['title']}]({paper_info['link']})**\n\n"
        f"> 🤖 **Llama-3.1 Summary:** {ai_summary}\n\n"
        f"{end_marker}"
    )

    pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    
    if start_marker not in content:
        print("Error: Markers not found in README.md.")
        return

    updated_content = re.sub(pattern, new_entry, content, flags=re.DOTALL)

    if updated_content != content:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(updated_content)
        print("README.md updated successfully.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    paper = get_latest_paper()
    summary = generate_summary(paper['title'], paper['abstract'])
    update_readme(paper, summary)
