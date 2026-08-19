import anthropic
import os
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, YOUR_NAME

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BASE_RESUME_PATH = os.path.join(os.path.dirname(__file__), "base_resume.txt")
TAILORED_DIR = os.path.join(os.path.dirname(__file__), "tailored_resumes")
os.makedirs(TAILORED_DIR, exist_ok=True)

def load_base_resume():
    if not os.path.exists(BASE_RESUME_PATH):
        raise FileNotFoundError(
            f"Put your resume as plain text at: {BASE_RESUME_PATH}"
        )
    with open(BASE_RESUME_PATH, "r") as f:
        return f.read()

def tailor_resume(job_title: str, company: str, jd_text: str):
    base_resume = load_base_resume()

    prompt = f"""You are an expert resume writer helping {YOUR_NAME} apply for a job.

Here is their current resume:
<resume>
{base_resume}
</resume>

Here is the job description:
<job_description>
Company: {company}
Role: {job_title}

{jd_text}
</job_description>

Your task:
1. Rewrite and tailor the resume to this specific job description.
2. Mirror keywords and phrases from the JD naturally (for ATS systems).
3. Reorder bullet points to put the most relevant experience first.
4. Adjust the professional summary to directly address what this company needs.
5. Do NOT invent experience or skills the candidate does not have.
6. Do NOT change names, dates, company names, or education facts.
7. Keep the same overall structure and length.
8. Output ONLY the complete tailored resume text — no commentary.

Tailored resume:"""

    print(f"  Tailoring resume for {job_title} at {company}...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    tailored_text = message.content[0].text.strip()

    safe_name = f"{company}_{job_title}".replace(" ", "_").replace("/", "-")[:60]
    save_path = os.path.join(TAILORED_DIR, f"{safe_name}.txt")
    with open(save_path, "w") as f:
        f.write(tailored_text)

    print(f"  Saved tailored resume → {save_path}")
    return tailored_text, save_path


if __name__ == "__main__":
    sample_jd = """
    We are looking for a Python Backend Engineer to join our team.
    You will build REST APIs using FastAPI, work with PostgreSQL databases,
    deploy on AWS, and write clean, well-tested code. Experience with Docker
    and Kubernetes is a plus. Strong communication skills required.
    """
    text, path = tailor_resume("Python Backend Engineer", "Acme Corp", sample_jd)
    print("\n--- Tailored Resume Preview ---")
    print(text[:500])
