# JobPilot

An autonomous AI job hunt agent with 3 agentic loops that finds jobs, tailors your resume, sends cold emails to recruiters, and triages your inbox — all on autopilot.

## What it does

### Loop 1 — Daily Job Search and Apply (9 AM)
- Scrapes 30 fresh jobs daily from LinkedIn, Indeed, and 80+ Fortune 500 careers pages
- Uses Claude to tailor your resume to each job description
- Filters for L4/mid-level roles posted within 24 hours
- Prevents duplicate applications

### Loop 2 — Recruiter Outreach (10 AM)
- Finds recruiter emails using Hunter.io
- Sends personalized cold emails via Gmail API
- Auto follow-up at day 7, day 14, and thank-you at day 21
- Caps at 5 cold emails per day

### Loop 3 — Inbox Triage (every hour)
- Reads Gmail and classifies job-related emails using Claude
- Auto-moves rejections to Job Rejections folder
- Flags interview invites for immediate attention

### Live Dashboard
- Real-time view of all jobs, application status, outreach tracker
- Apply button opens job URL directly
- Resume button shows your tailored resume for that role
- Mark Applied and Delete buttons for pipeline management
- Accessible via ngrok from anywhere

## Tech Stack

- AI: Claude API (claude-sonnet-4-6)
- Email: Gmail API (Google OAuth)
- Recruiter lookup: Hunter.io API
- Scraping: BeautifulSoup, Requests
- Auto-apply: Playwright (Chromium)
- Database: SQLite
- Scheduler: Python cron
- Dashboard: Python HTTP server + ngrok

## Setup

### 1. Install dependencies
pip3 install anthropic requests beautifulsoup4 schedule python-dotenv playwright google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
python3 -m playwright install chromium

### 2. Configure
cp config.template.py config.py
Fill in your API keys and details in config.py

Required keys:
- ANTHROPIC_API_KEY from console.anthropic.com
- HUNTER_API_KEY from hunter.io (free: 25/month)
- Gmail OAuth credentials (see Gmail API Setup below)

### 3. Gmail API Setup
1. Go to console.cloud.google.com
2. Create a project, enable Gmail API
3. Create OAuth credentials (Desktop app)
4. Download as credentials.json and place in project folder

### 4. Add your resume
Paste your full resume as plain text into base_resume.txt

### 5. Initialize database
python3 database.py

### 6. Run
python3 orchestrator.py       # Run everything on schedule
python3 apply_loop.py         # Find and log 30 jobs
python3 email_scheduler.py    # Send cold emails
python3 inbox_triage.py       # Classify inbox
python3 dashboard.py          # Start dashboard at localhost:8080

### 7. Public dashboard (optional)
brew install ngrok
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8080

## Daily Routine (5 minutes)

1. Open dashboard URL
2. Click Apply on interesting jobs, upload tailored resume, submit
3. Click Mark Applied when done
4. Click Delete on roles you dont want
5. Cron handles everything else automatically

## Project Structure

```
job_hunt_agent/
├── config.template.py         Configuration template (copy to config.py)
├── database.py                SQLite state store
├── resume_tailor.py           Claude resume tailoring
├── job_scraper.py             LinkedIn + Indeed scraper
├── fortune500_scraper.py      Fortune 500 careers page scraper
├── resume_query_generator.py  Claude-powered search query generator
├── apply_loop.py              Loop 1 orchestrator
├── email_finder.py            Hunter.io recruiter email lookup
├── cold_email.py              Claude cold email writer
├── email_scheduler.py         Loop 2 Gmail email sender
├── inbox_triage.py            Loop 3 Gmail inbox classifier
├── auto_apply.py              Playwright auto-apply
├── dashboard.py               Live web dashboard
├── orchestrator.py            Master scheduler
└── base_resume.txt            Your base resume (not committed)
```

## Cost

Around 13 cents per day (about 4 dollars per month) in Claude API costs. Everything else is free.

## Results Day 1

- 90+ jobs scraped and logged
- Resumes tailored for every role
- 21 cold emails sent to recruiters at Snap, Google, OpenAI, Uber, Robinhood, HackerRank, Figma, Vercel
- 3 rejections auto-moved from inbox

## Built by

Vamsi Krishna V
LinkedIn: https://linkedin.com/in/vamsivadlamudi
GitHub: https://github.com/rvadlamudiv-maker
