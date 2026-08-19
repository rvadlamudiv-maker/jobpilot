import anthropic
import json
import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from database import is_email_processed, log_inbox_email, update_application_status, get_all_applications
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, REJECTION_FOLDER

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels"
]

def get_gmail_service():
    creds = None
    token_path = "token.json"
    creds_path = "credentials.json"
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_recent_emails(service, max_results=50):
    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q="newer_than:7d"
    ).execute()
    messages = results.get("messages", [])
    emails = []
    for msg in messages[:20]:
        try:
            full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
            subject = headers.get("Subject", "")
            from_addr = headers.get("From", "")
            date = headers.get("Date", "")
            body = ""
            payload = full.get("payload", {})
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        data = part.get("body", {}).get("data", "")
                        if data:
                            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")[:500]
                            break
            elif payload.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")[:500]
            emails.append({
                "message_id": msg["id"],
                "from": from_addr,
                "subject": subject,
                "date": date,
                "body_preview": body,
                "label_ids": full.get("labelIds", [])
            })
        except Exception as e:
            print(f"  Error reading email {msg['id']}: {e}")
    return emails

def classify_email(from_address, subject, body):
    prompt = f"""Classify this email for a job seeker. Categories:
- interview_invite: scheduling an interview or assessment
- screening: HR or recruiter reaching out to proceed
- rejection: declining the application
- offer: a job offer
- noise: unrelated to job applications
- other: job-related but doesn't fit above

FROM: {from_address}
SUBJECT: {subject}
BODY: {body[:600]}

Respond ONLY with JSON: {{"classification": "rejection", "summary": "Rejection from Stripe"}}"""
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

def get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]
    new_label = service.users().labels().create(
        userId="me",
        body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    ).execute()
    return new_label["id"]

def move_email_to_label(service, message_id, label_name):
    try:
        label_id = get_or_create_label(service, label_name)
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]}
        ).execute()
        print(f"    Moved to '{label_name}'")
    except Exception as e:
        print(f"    Could not move email: {e}")

def run_inbox_triage():
    print("\n-- Inbox triage loop starting --")
    try:
        service = get_gmail_service()
    except Exception as e:
        print(f"Gmail auth error: {e}")
        print("Make sure credentials.json is in your project folder.")
        return

    emails = get_recent_emails(service)
    print(f"Found {len(emails)} recent emails to check")

    interviews = []
    rejections = []

    for email in emails:
        msg_id = email["message_id"]
        from_addr = email["from"]
        subject = email["subject"]
        date = email["date"]
        body = email["body_preview"]

        if is_email_processed(msg_id):
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
            move_email_to_label(service, msg_id, REJECTION_FOLDER)
            action = "moved_to_rejection_folder"
        elif classification == "offer":
            interviews.append({"subject": subject, "from": from_addr, "summary": "JOB OFFER: " + summary})
            if app_id:
                update_application_status(app_id, "offer")
            action = "notification_sent"
        else:
            action = "no_action"

        log_inbox_email(msg_id, from_addr, subject, date, classification, action, app_id)

    print(f"\n-- Triage complete --")
    print(f"  Interviews/Screenings: {len(interviews)}")
    for i in interviews:
        print(f"    NOTIFY: {i['subject']} from {i['from']}")
    print(f"  Rejections moved: {len(rejections)}")
    return {"interviews": interviews, "rejections": rejections}

if __name__ == "__main__":
    run_inbox_triage()
