code = """import anthropic
import json
from database import is_email_processed, log_inbox_email, update_application_status, get_all_applications
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, REJECTION_FOLDER

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
GMAIL_MCP_URL = "https://gmailmcp.googleapis.com/mcp/v1"

def classify_email(from_address, subject, body):
    prompt = f\"\"\"Classify this email for a job seeker. Categories:
- interview_invite: scheduling an interview or assessment
- screening: HR or recruiter reaching out to proceed  
- rejection: declining the application
- offer: a job offer
- noise: unrelated to job applications
- other: job-related but doesn't fit above

FROM: {from_address}
SUBJECT: {subject}
BODY: {body[:800]}

Respond ONLY with JSON like: {{"classification": "rejection", "summary": "Rejection from Stripe"}}\"\"\"
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(msg.content[0].text.strip())
    except Exception:
        return {"classification": "other", "summary": "Could not parse"}

def match_application(from_address):
    apps = get_all_applications()
    from_domain = from_address.split("@")[-1].lower() if "@" in from_address else ""
    for app in apps:
        company_lower = app["company"].lower().replace(" ", "")
        if company_lower in from_domain or from_domain.startswith(company_lower[:6]):
            return app["id"]
    return None

def _move_email_to_label(message_id, label_name):
    try:
        client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": f"Apply Gmail label '{label_name}' to message ID {message_id}. Create it if needed. Then archive the message."}],
            mcp_servers=[{"type": "url", "url": GMAIL_MCP_URL, "name": "gmail"}]
        )
        print(f"    Moved {message_id} to '{label_name}'")
    except Exception as e:
        print(f"    Could not move email: {e}")

def run_inbox_triage():
    print("\\n-- Inbox triage loop starting --")
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system="You are an inbox triage agent. Search Gmail for job-related emails from the last 7 days. Return a JSON array with fields: message_id, from, subject, date, body_preview.",
        messages=[{"role": "user", "content": "Search my Gmail for job-related emails in the last 7 days. Return as JSON array."}],
        mcp_servers=[{"type": "url", "url": GMAIL_MCP_URL, "name": "gmail"}]
    )

    emails_raw = []
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            try:
                text = block.text.strip()
                start = text.find("[")
                end = text.rfind("]") + 1
                if start != -1 and end > start:
                    emails_raw = json.loads(text[start:end])
                    break
            except Exception:
                pass

    print(f"Found {len(emails_raw)} job-related emails")
    interviews = []
    rejections = []

    for email in emails_raw:
        msg_id = email.get("message_id") or email.get("id", "")
        from_addr = email.get("from", "")
        subject = email.get("subject", "")
        date = email.get("date", "")
        body = email.get("body_preview", "")

        if not msg_id or is_email_processed(msg_id):
            continue

        result = classify_email(from_addr, subject, body)
        classification = result.get("classification", "other")
        summary = result.get("summary", "")
        print(f"  [{classification.upper()}] {subject[:60]}")

        app_id = match_application(from_addr)

        if classification in ("interview_invite", "screening"):
            interviews.append({"subject": subject, "from": from_addr, "summary": summary})
            if app_id:
                update_application_status(app_id, "interview" if classification == "interview_invite" else "screening")
            action = "notification_sent"
        elif classification == "rejection":
            rejections.append({"subject": subject, "from": from_addr})
            if app_id:
                update_application_status(app_id, "rejected")
            action = "moved_to_rejection_folder"
            _move_email_to_label(msg_id, REJECTION_FOLDER)
        elif classification == "offer":
            interviews.append({"subject": subject, "from": from_addr, "summary": "JOB OFFER: " + summary})
            if app_id:
                update_application_status(app_id, "offer")
            action = "notification_sent"
        else:
            action = "no_action"

        log_inbox_email(msg_id, from_addr, subject, date, classification, action, app_id)

    print(f"\\n-- Triage complete --")
    print(f"  Interviews/Screenings: {len(interviews)}")
    print(f"  Rejections moved: {len(rejections)}")
    return {"interviews": interviews, "rejections": rejections}

if __name__ == "__main__":
    run_inbox_triage()
"""

with open("inbox_triage.py", "w") as f:
    f.write(code)
print("inbox_triage.py written successfully")
