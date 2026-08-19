import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "state.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title       TEXT NOT NULL,
            company         TEXT NOT NULL,
            job_url         TEXT UNIQUE,
            job_board       TEXT,
            status          TEXT DEFAULT 'applied',
            applied_at      TEXT NOT NULL,
            resume_used     TEXT,
            jd_text         TEXT,
            notes           TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS email_outreach (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id      INTEGER REFERENCES applications(id),
            recruiter_name      TEXT,
            recruiter_email     TEXT,
            company             TEXT,
            cold_email_sent_at  TEXT,
            followup1_sent_at   TEXT,
            followup2_sent_at   TEXT,
            thankyou_sent_at    TEXT,
            last_reply_at       TEXT,
            notes               TEXT,
            status              TEXT DEFAULT 'pending'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS inbox_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_message_id TEXT UNIQUE,
            from_address     TEXT,
            subject          TEXT,
            received_at      TEXT,
            classification   TEXT,
            action_taken     TEXT,
            application_id   INTEGER REFERENCES applications(id)
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized")

def already_applied(job_url, job_title=None, company=None):
    conn = get_conn()
    row = conn.execute("SELECT id FROM applications WHERE job_url = ?", (job_url,)).fetchone()
    if row:
        conn.close()
        return True
    if job_title and company:
        row = conn.execute(
            "SELECT id FROM applications WHERE job_title = ? AND company = ?",
            (job_title, company)
        ).fetchone()
        if row:
            conn.close()
            return True
    conn.close()
    return False

def log_application(job_title, company, job_url, job_board, resume_path, jd_text):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO applications (job_title, company, job_url, job_board, applied_at, resume_used, jd_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job_title, company, job_url, job_board, datetime.utcnow().isoformat(), resume_path, jd_text))
        conn.commit()
        app_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return app_id
    except sqlite3.IntegrityError:
        print(f"Already applied to {job_url} — skipping")
        return None
    finally:
        conn.close()

def update_application_status(application_id, status):
    conn = get_conn()
    conn.execute("UPDATE applications SET status = ? WHERE id = ?", (status, application_id))
    conn.commit()
    conn.close()

def get_all_applications():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM applications ORDER BY applied_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_outreach(application_id, recruiter_name, recruiter_email, company):
    conn = get_conn()
    conn.execute("""
        INSERT INTO email_outreach (application_id, recruiter_name, recruiter_email, company, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (application_id, recruiter_name, recruiter_email, company))
    conn.commit()
    conn.close()

def get_pending_outreach():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM email_outreach WHERE status = 'pending'").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_followup1_due(days=7):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM email_outreach
        WHERE status = 'cold_sent'
        AND cold_email_sent_at <= datetime('now', ? || ' days')
    """, (f"-{days}",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_followup2_due(days=7):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM email_outreach
        WHERE status = 'followup1_sent'
        AND followup1_sent_at <= datetime('now', ? || ' days')
    """, (f"-{days}",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_thankyou_due(days=7):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM email_outreach
        WHERE status = 'followup2_sent'
        AND followup2_sent_at <= datetime('now', ? || ' days')
    """, (f"-{days}",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_email_sent(outreach_id, stage):
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    field_map = {
        "cold":      ("cold_email_sent_at",  "cold_sent"),
        "followup1": ("followup1_sent_at",   "followup1_sent"),
        "followup2": ("followup2_sent_at",   "followup2_sent"),
        "thankyou":  ("thankyou_sent_at",    "thankyou_sent"),
    }
    ts_col, new_status = field_map[stage]
    conn.execute(f"UPDATE email_outreach SET {ts_col} = ?, status = ? WHERE id = ?",
                 (now, new_status, outreach_id))
    conn.commit()
    conn.close()

def log_inbox_email(gmail_message_id, from_address, subject, received_at, classification, action_taken, application_id=None):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO inbox_log
            (gmail_message_id, from_address, subject, received_at, classification, action_taken, application_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (gmail_message_id, from_address, subject, received_at, classification, action_taken, application_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def is_email_processed(gmail_message_id):
    conn = get_conn()
    row = conn.execute("SELECT id FROM inbox_log WHERE gmail_message_id = ?", (gmail_message_id,)).fetchone()
    conn.close()
    return row is not None

if __name__ == "__main__":
    init_db()
