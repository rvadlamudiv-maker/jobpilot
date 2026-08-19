import anthropic
import os
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, YOUR_NAME, YOUR_EMAIL, YOUR_LINKEDIN, YOUR_GITHUB

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def _call_claude(prompt, max_tokens=500):
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

def write_cold_outreach(recruiter_name, company, job_title, jd_snippet):
    prompt = f"""Write a short cold outreach email from {YOUR_NAME} to {recruiter_name} at {company}.

Context:
- {YOUR_NAME} just applied for the {job_title} role at {company}
- LinkedIn: {YOUR_LINKEDIN}
- GitHub: {YOUR_GITHUB}

Job description snippet:
{jd_snippet[:400]}

Rules:
- Subject line: short and specific
- Start with: "Hi [recruiter first name]," on its own line
- Body: 4-5 sentences MAX
- Second line: something specific about {company}
- One concrete reason why {YOUR_NAME} is a fit for THIS role
- End with: "Would love 15 minutes if you have bandwidth"
- Sign off with: "Best,\n{YOUR_NAME}\nLinkedIn: [link]\nGitHub: [link]"
- NO generic openers like "I hope this email finds you well"
- NO buzzwords like "passionate", "rockstar", "ninja"
- Sound like a real person

Output ONLY in this format:
SUBJECT: <subject line>
BODY:
<email body>"""

    raw = _call_claude(prompt)
    lines = raw.split("\n")
    subject = ""
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)
    return {"subject": subject, "body": "\n".join(body_lines).strip()}

def write_followup(recruiter_name, company, job_title, original_subject):
    prompt = f"""Write a short follow-up email from {YOUR_NAME} to {recruiter_name} at {company}.

Context:
- Sent a cold email about the {job_title} role 2-3 days ago (subject: "{original_subject}")
- No response yet

Rules:
- Start with: Hi [recruiter first name],
- 3 sentences MAX
- Reference the original email naturally
- Add ONE new piece of value: a relevant project link or insight
- Same low-pressure ask
- No apologies for following up

Output ONLY in this format:
SUBJECT: Re: {original_subject}
BODY:
<email body>"""

    raw = _call_claude(prompt)
    lines = raw.split("\n")
    subject = f"Re: {original_subject}"
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)
    return {"subject": subject, "body": "\n".join(body_lines).strip()}

def write_thankyou(recruiter_name, company, job_title, original_subject):
    prompt = f"""Write a brief closing email from {YOUR_NAME} to {recruiter_name} at {company}.

Context:
- Applied for {job_title}, sent cold email and follow-up, no response
- This is the final graceful sign-off

Rules:
- Start with: Hi [recruiter first name],
- 2-3 sentences only
- Genuinely warm, zero resentment
- Leave door open for future opportunities at {company}

Output ONLY in this format:
SUBJECT: Re: {original_subject}
BODY:
<email body>"""

    raw = _call_claude(prompt)
    lines = raw.split("\n")
    subject = f"Re: {original_subject}"
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)
    return {"subject": subject, "body": "\n".join(body_lines).strip()}

if __name__ == "__main__":
    email = write_cold_outreach(
        recruiter_name="Sarah",
        company="Stripe",
        job_title="Backend Engineer",
        jd_snippet="Build the financial infrastructure of the internet using Python and Go."
    )
    print("SUBJECT:", email["subject"])
    print("\nBODY:\n", email["body"])
