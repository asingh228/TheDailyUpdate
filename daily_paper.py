import os
import feedparser
from openai import OpenAI
from datetime import datetime

# --- CONFIGURATION ---
ARXIV_URL = 'http://export.arxiv.org/api/query?search_query=cat:cs.LG&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending'
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
MODEL_ID = "llama3.1-8b"
FILENAME = "README.md"
# CRITICAL: This tag must match what is in your README exactly.
ANCHOR_TAG = ""

def get_latest_paper():
    print(f"Fetching latest paper from: {ARXIV_URL}")
    data = feedparser.parse(ARXIV_URL)
    
    if not data.entries:
        print("Error: No papers found on ArXiv.")
        return None
        
    paper = data.entries[0]
    return {
        "title": paper.title.replace("\n", " "),
        "abstract": paper.summary.replace("\n", " "),
        "link": paper.link.strip(), # Remove any trailing spaces
        "date": datetime.now().strftime("%Y-%m-%d")
    }

def generate_simple_summary(paper_title, paper_abstract):
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        print("Error: CEREBRAS_API_KEY missing.")
        return None

    client = OpenAI(base_url=CEREBRAS_BASE_URL, api_key=api_key)

    prompt = (
        f"Explain the following AI research paper to a non-technical audience (like a business manager or curious student). "
        f"Avoid jargon. Explain 'what it does' and 'why it matters' in 2-3 clear, engaging sentences.\n\n"
        f"Title: {paper_title}\n"
        f"Abstract: {paper_abstract}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "You are a clear, helpful AI science communicator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        if not content: 
            return None
        return content
    except Exception as e:
        print(f"API Error: {e}")
        return None

def update_readme(paper, summary):
    if not os.path.exists(FILENAME):
        print("README.md not found.")
        return

    with open(FILENAME, "r", encoding="utf-8") as file:
        content = file.read()

    if ANCHOR_TAG not in content:
        print(f"Error: Anchor tag '{ANCHOR_TAG}' not found in README.")
        return

    # IDEMPOTENCY CHECK
    if paper['link'] in content:
        print(f"Skipping update: The paper '{paper['title']}' is already in the README.")
        return

    new_entry = (
        f"\n\n### ⚡ {paper['date']}: {paper['title']}\n"
        f"> **Simple Summary:** {summary}\n\n"
        f"[Read Full Paper]({paper['link']})\n"
        f"---" 
    )

    # CRITICAL FIX: The '1' argument ensures we only replace the FIRST tag found.
    # This prevents duplication if the tag exists multiple times in the file.
    updated_content = content.replace(ANCHOR_TAG, f"{ANCHOR_TAG}{new_entry}", 1)

    with open(FILENAME, "w", encoding="utf-8") as file:
        file.write(updated_content)
    print("Success: New paper added to the top of the list.")

if __name__ == "__main__":
    paper = get_latest_paper()
    
    if paper:
        # Pre-check to save API credits
        if os.path.exists(FILENAME):
            with open(FILENAME, "r", encoding="utf-8") as f:
                if paper['link'] in f.read():
                     print(f"Skipping API Call: Paper '{paper['title']}' already exists.")
                     exit(0)

        summary = generate_simple_summary(paper['title'], paper['abstract'])
        
        if summary:
            update_readme(paper, summary)
        else:
            print("Failed to generate summary. Skipping update.")
    else:
        print("Failed to fetch paper. Skipping update.")
