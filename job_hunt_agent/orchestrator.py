import schedule
import time
from datetime import datetime
from database import init_db
from config import DAILY_JOB_SEARCH_TIME, INBOX_CHECK_INTERVAL_MINUTES

def job_loop():
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Running Loop 1 + Loop 2")
    print('='*50)
    try:
        from apply_loop import run_apply_loop
        run_apply_loop()
    except Exception as e:
        print(f"Loop 1 error: {e}")
    try:
        from email_scheduler import run_email_scheduler
        run_email_scheduler()
    except Exception as e:
        print(f"Loop 2 error: {e}")

def inbox_loop():
    print(f"\n[{datetime.now().strftime('%H:%M')}] Running inbox triage...")
    try:
        from inbox_triage import run_inbox_triage
        run_inbox_triage()
    except Exception as e:
        print(f"Loop 3 error: {e}")

def main():
    print("JobPilot starting up...")
    init_db()
    schedule.every().day.at(DAILY_JOB_SEARCH_TIME).do(job_loop)
    print(f"Loop 1+2 scheduled at {DAILY_JOB_SEARCH_TIME} daily")
    schedule.every(INBOX_CHECK_INTERVAL_MINUTES).minutes.do(inbox_loop)
    print(f"Loop 3 every {INBOX_CHECK_INTERVAL_MINUTES} minutes")
    print("\nRunning all loops once on startup...\n")
    job_loop()
    inbox_loop()
    print("\nJobPilot running. Press Ctrl+C to stop.\n")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
