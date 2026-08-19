import time
import random
from job_scraper import scrape_all_jobs
from fortune500_scraper import scrape_fortune500_jobs
from resume_tailor import tailor_resume
from database import already_applied, log_application, create_outreach
from email_finder import find_recruiter_email
from auto_apply import run_auto_apply
from config import JOBS_PER_DAY

def run_apply_loop():
    print("\n====== Loop 1: Daily Job Search & Apply ======")

    print("\n[Source 1] Scraping LinkedIn + Indeed...")
    linkedin_jobs = scrape_all_jobs(jobs_per_day=JOBS_PER_DAY // 2)

    print("\n[Source 2] Scraping Fortune 500 careers pages...")
    fortune_jobs = scrape_fortune500_jobs(jobs_per_day=JOBS_PER_DAY // 2)

    all_listings = linkedin_jobs + fortune_jobs
    print(f"\nTotal listings found: {len(all_listings)}")

    applied_count = 0
    skipped_count = 0

    for job in all_listings:
        if applied_count >= JOBS_PER_DAY:
            break
        if already_applied(job.job_url, job.title, job.company):
            skipped_count += 1
            continue
        if not job.jd_text or len(job.jd_text) < 100:
            print(f"  Skipping {job.title} @ {job.company} — JD too short")
            continue

        print(f"\n[{applied_count + 1}] {job.title} @ {job.company} ({job.job_board})")

        try:
            _, resume_path = tailor_resume(job.title, job.company, job.jd_text)
            app_id = log_application(
                job_title=job.title,
                company=job.company,
                job_url=job.job_url,
                job_board=job.job_board,
                resume_path=resume_path,
                jd_text=job.jd_text
            )

            if app_id:
                print(f"  Logged application ID {app_id}")

                # Auto-apply on company careers pages only (not LinkedIn)
                if job.job_board == "company_careers":
                    print(f"  Attempting auto-apply on {job.company} careers page...")
                    success = run_auto_apply(
                        job_url=job.job_url,
                        job_board=job.job_board,
                        company=job.company,
                        resume_path=resume_path,
                        headless=True
                    )
                    if success:
                        print(f"  Auto-applied successfully!")
                    else:
                        print(f"  Auto-apply failed — screenshot saved for manual review")
                else:
                    print(f"  LinkedIn job — open manually to apply: {job.job_url}")

                # Find recruiter for cold email
                recruiter = find_recruiter_email(job.company, job.job_url)
                if recruiter and recruiter.get("email"):
                    create_outreach(
                        application_id=app_id,
                        recruiter_name=recruiter.get("name", ""),
                        recruiter_email=recruiter.get("email", ""),
                        company=job.company
                    )
                    print(f"  Recruiter: {recruiter.get('email')} — queued for outreach")
                else:
                    print(f"  No recruiter email found for {job.company}")

                applied_count += 1

        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(random.uniform(2, 4))

    print(f"\n====== Loop 1 done: {applied_count} applied, {skipped_count} skipped ======")
    return applied_count

if __name__ == "__main__":
    run_apply_loop()
