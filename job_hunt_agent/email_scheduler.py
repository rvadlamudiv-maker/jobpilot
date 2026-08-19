import anthropic
import base64
import os
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from database import get_pending_outreach, get_followup1_due, get_followup2_due, get_thankyou_due, mark_email_sent, get_conn
from cold_email import write_cold_outreach, write_followup, write_thankyou
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, YOUR_EMAIL

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels"
]

def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def send_email_via_gmail(service, to, subject, body):
    try:
        message = MIMEText(body)
        message["to"] = to
        message["from"] = YOUR_EMAIL
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()
        print(f"    Sent to {to}: {subject}")
        return True
    except Exception as e:
        print(f"    Failed to send to {to}: {e}")
        return False

def write_followup2(recruiter_name, company, job_title, original_subject):
    import anthropic
    from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, YOUR_NAME, YOUR_LINKEDIN, YOUR_GITHUB
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""Write a second follow-up email from {YOUR_NAME} to {recruiter_name} at {company}.

Context:
- Applied for {job_title}, sent cold email and first follow-up
- Still no response after 14 days
- This is the final follow-up before a thank-you

Rules:
- 3 sentences MAX
- Acknowledge they are busy
- Add one more piece of value: a different project or achievement
- Keep it warm and professional
- No desperation

Output ONLY in this format:
SUBJECT: Re: {original_subject}
BODY:
<email body>"""
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        messages=[{{"role": "user", "content": prompt}}]
    )
    raw = msg.content[0].text.strip()
    lines = raw.split("\n")
    subject = f"Re: {{original_subject}}"
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)
    return {{"subject": subject, "body": "\n".join(body_lines).strip()}}

def run_email_scheduler(dry_run=False):
    print("\n-- Email scheduler running --")
    service = get_gmail_service()

    # Phase 1: Cold emails
    pending = get_pending_outreach()
    print(f"  Pending cold emails: {0}")
    for row in pending:
        conn = get_conn()
        app = conn.execute(
            "SELECT jd_text, job_title FROM applications WHERE id = ?",
            (row["application_id"],)
        ).fetchone()
        conn.close()
        jd_snippet = app["jd_text"][:400] if app else ""
        job_title = app["job_title"] if app else row["company"]
        email = write_cold_outreach(
            recruiter_name=row["recruiter_name"] or "there",
            company=row["company"],
            job_title=job_title,
            jd_snippet=jd_snippet
        )
        if not dry_run:
            sent = send_email_via_gmail(service, row["recruiter_email"], email["subject"], email["body"])
            if sent:
                mark_email_sent(row["id"], "cold")
                conn = get_conn()
                conn.execute("UPDATE email_outreach SET notes = ? WHERE id = ?", (email["subject"], row["id"]))
                conn.commit()
                conn.close()
        else:
            print(f"    [DRY RUN] To: {{row['recruiter_email']}}")
            print(f"    [DRY RUN] Subject: {{email['subject']}}")

    # Phase 2: Follow-up 1 (7 days after cold)
    followups1 = get_followup1_due(days=7)
    print(f"\n  Follow-up 1 due: {len(followups1)}")
    for row in followups1:
        conn = get_conn()
        r = conn.execute("SELECT notes, job_title FROM email_outreach e JOIN applications a ON e.application_id = a.id WHERE e.id = ?", (row["id"],)).fetchone()
        conn.close()
        original_subject = row.get("notes") or f"Application to {{row['company']}}"
        job_title = r["job_title"] if r else row["company"]
        email = write_followup(
            recruiter_name=row["recruiter_name"] or "there",
            company=row["company"],
            job_title=job_title,
            original_subject=original_subject
        )
        if not dry_run:
            sent = send_email_via_gmail(service, row["recruiter_email"], email["subject"], email["body"])
            if sent:
                mark_email_sent(row["id"], "followup1")
        else:
            print(f"    [DRY RUN] Follow-up 1 to {{row['recruiter_email']}}")

    # Phase 3: Follow-up 2 (7 days after follow-up 1)
    followups2 = get_followup2_due(days=7)
    print(f"\n  Follow-up 2 due: {len(followups2)}")
    for row in followups2:
        conn = get_conn()
        r = conn.execute("SELECT notes, job_title FROM email_outreach e JOIN applications a ON e.application_id = a.id WHERE e.id = ?", (row["id"],)).fetchone()
        conn.close()
        original_subject = row.get("notes") or f"Application to {{row['company']}}"
        job_title = r["job_title"] if r else row["company"]
        email = write_followup2(
            recruiter_name=row["recruiter_name"] or "there",
            company=row["company"],
            job_title=job_title,
            original_subject=original_subject
        )
        if not dry_run:
            sent = send_email_via_gmail(service, row["recruiter_email"], email["subject"], email["body"])
            if sent:
                mark_email_sent(row["id"], "followup2")
        else:
            print(f"    [DRY RUN] Follow-up 2 to {{row['recruiter_email']}}")

    # Phase 4: Thank-you (7 days after follow-up 2)
    thankyous = get_thankyou_due(days=7)
    print(f"\n  Thank-you emails due: {len(thankyous)}")
    for row in thankyous:
        conn = get_conn()
        r = conn.execute("SELECT notes, job_title FROM email_outreach e JOIN applications a ON e.application_id = a.id WHERE e.id = ?", (row["id"],)).fetchone()
        conn.close()
        original_subject = row.get("notes") or f"Application to {{row['company']}}"
        job_title = r["job_title"] if r else row["company"]
        email = write_thankyou(
            recruiter_name=row["recruiter_name"] or "there",
            company=row["company"],
            job_title=job_title,
            original_subject=original_subject
        )
        if not dry_run:
            sent = send_email_via_gmail(service, row["recruiter_email"], email["subject"], email["body"])
            if sent:
                mark_email_sent(row["id"], "thankyou")
        else:
            print(f"    [DRY RUN] Thank-you to {{row['recruiter_email']}}")

    print("\n-- Email scheduler done --")

if __name__ == "__main__":
    run_email_scheduler(dry_run=False)
