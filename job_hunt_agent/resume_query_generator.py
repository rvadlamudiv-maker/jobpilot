import anthropic
import json
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def extract_resume_queries(resume_path="base_resume.txt"):
    with open(resume_path, "r") as f:
        resume = f.read()

    prompt = f"""You are a job search expert. Read this resume carefully and generate the best job search queries for this person.

Resume:
{resume}

Your task:
1. Identify the top skills, technologies, and experience areas from the resume
2. Generate 8-10 specific job title search queries that would find the BEST matching roles
3. Focus on what this person is actually strong at — not generic titles
4. Include both traditional titles and modern AI/ML titles if relevant
5. Make queries short — 2-4 words max each

Return ONLY a JSON array of strings like:
["Backend Engineer", "AI Engineer", "Platform Engineer", "LLM Engineer", "Distributed Systems Engineer", "Python Engineer", "Infrastructure Engineer", "ML Platform Engineer"]"""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    text = msg.content[0].text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    queries = json.loads(text[start:end])
    return queries

if __name__ == "__main__":
    queries = extract_resume_queries()
    print("Generated search queries based on your resume:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")

    # Auto-update config.py with these queries
    with open("config.py", "r") as f:
        content = f.read()

    import re
    new_queries = json.dumps(queries, indent=4)
    new_block = f"JOB_SEARCH_QUERIES = {new_queries}"
    content = re.sub(
        r"JOB_SEARCH_QUERIES = \[.*?\]",
        new_block,
        content,
        flags=re.DOTALL
    )
    with open("config.py", "w") as f:
        f.write(content)
    print("\nconfig.py updated with resume-matched queries!")
