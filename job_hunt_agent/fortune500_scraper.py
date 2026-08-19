import requests
from bs4 import BeautifulSoup
import time
import random
from dataclasses import dataclass
from typing import List
from config import JOB_SEARCH_QUERIES

@dataclass
class JobListing:
    title: str
    company: str
    location: str
    job_url: str
    job_board: str
    jd_text: str = ""

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

FORTUNE500_CAREERS = {
    "Google":       "https://careers.google.com/jobs/results/?q={query}",
    "Meta":         "https://www.metacareers.com/jobs?q={query}",
    "Apple":        "https://jobs.apple.com/en-us/search?search={query}",
    "Amazon":       "https://www.amazon.jobs/en/search?base_query={query}",
    "Microsoft":    "https://jobs.careers.microsoft.com/global/en/search?q={query}",
    "Stripe":       "https://stripe.com/jobs/search?q={query}",
    "Netflix":      "https://jobs.netflix.com/search?q={query}",
    "Uber":         "https://www.uber.com/us/en/careers/list/?q={query}",
    "Airbnb":       "https://careers.airbnb.com/positions/?search={query}",
    "Shopify":      "https://www.shopify.com/careers/search?keywords={query}",
    "Salesforce":   "https://careers.salesforce.com/en/jobs/?search={query}",
    "Oracle":       "https://careers.oracle.com/jobs/#en/sites/jobsearch/jobs?keyword={query}",
    "IBM":          "https://www.ibm.com/employment/#jobs?q={query}",
    "Intel":        "https://jobs.intel.com/en/search-jobs/{query}",
    "Nvidia":       "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite?q={query}",
    "Databricks":   "https://www.databricks.com/company/careers/open-positions?department=Engineering&search={query}",
    "Snowflake":    "https://careers.snowflake.com/us/en/search-results?keywords={query}",
    "Palantir":     "https://www.palantir.com/careers/teams/engineering/?search={query}",
    "Coinbase":     "https://www.coinbase.com/careers/positions?department=Engineering&search={query}",
    "OpenAI":       "https://openai.com/careers/search?q={query}",
    "Anthropic":    "https://www.anthropic.com/careers#open-roles",
    "DoorDash":     "https://careers.doordash.com/jobs?search={query}",
    "Robinhood":    "https://careers.robinhood.com/open-positions?search={query}",
    "Vercel":       "https://vercel.com/careers#{query}",
    "Figma":        "https://www.figma.com/careers/#job-openings",
    "Notion":       "https://www.notion.so/careers#{query}",
    "Twilio":       "https://www.twilio.com/en-us/company/jobs?search={query}",
    "Datadog":      "https://careers.datadoghq.com/all-jobs/?search={query}",
    "GitHub":       "https://github.com/about/careers",
    "Atlassian":    "https://www.atlassian.com/company/careers/all-jobs?search={query}",
    "HubSpot":      "https://www.hubspot.com/careers/jobs?search={query}",
    "Slack":        "https://slack.com/intl/en-us/careers#{query}",
    "Zoom":         "https://careers.zoom.us/jobs?search={query}",
    "Dropbox":      "https://jobs.dropbox.com/all-jobs?search={query}",
    "Box":          "https://careers.box.com/us/en/search-results?keywords={query}",
    "Reddit":       "https://www.redditinc.com/careers",
    "Twitch":       "https://www.twitch.tv/jobs/en/",
    "Snap":         "https://snap.com/en-US/jobs?search={query}",
    "Pinterest":    "https://www.pinterestcareers.com/jobs/?search={query}",
    "Lyft":         "https://www.lyft.com/careers/engineering?search={query}",
    "Twitter":      "https://careers.x.com/en/jobs?search={query}",
    "Instacart":    "https://instacart.careers/jobs/?search={query}",
    "Brex":         "https://www.brex.com/careers#{query}",
    "Rippling":     "https://www.rippling.com/careers#{query}",
    "Scale":        "https://scale.com/careers#{query}",
    "Plaid":        "https://plaid.com/careers/openings/#{query}",
    "Gusto":        "https://gusto.com/about/careers#{query}",
    "Asana":        "https://asana.com/jobs/all-departments#{query}",
    "Monday":       "https://monday.com/l/careers/open-positions/?search={query}",
    "Zendesk":      "https://jobs.zendesk.com/us/en/search-results?keywords={query}",
    "Cloudflare":   "https://www.cloudflare.com/careers/jobs/?search={query}",
    "HashiCorp":    "https://www.hashicorp.com/careers/open-positions#{query}",
    "Okta":         "https://www.okta.com/company/careers/engineering/#{query}",
    "CrowdStrike":  "https://careers.crowdstrike.com/us/en/search-results?keywords={query}",
    "Palo Alto":    "https://jobs.paloaltonetworks.com/en/jobs/?search={query}",
    "ServiceNow":   "https://careers.servicenow.com/careers/jobs?search={query}",
    "Workday":      "https://wd5.myworkdayjobs.com/Workday?q={query}",
    "Adobe":        "https://careers.adobe.com/us/en/search-results?keywords={query}",
    "VMware":       "https://careers.vmware.com/search-jobs/{query}",
    "Dell":         "https://jobs.dell.com/search-jobs/{query}",
    "HP":           "https://jobs.hp.com/en-us/search-jobs/{query}",
    "Cisco":        "https://jobs.cisco.com/jobs/SearchJobs/{query}",
    "Qualcomm":     "https://careers.qualcomm.com/careers/search?keywords={query}",
    "AMD":          "https://careers.amd.com/careers-home/jobs?keywords={query}",
    "Texas Instruments": "https://careers.ti.com/search-jobs/{query}",
    "Broadcom":     "https://careers.broadcom.com/careers/search?keywords={query}",
    "SpaceX":       "https://www.spacex.com/careers/search/?search={query}",
    "Tesla":        "https://www.tesla.com/careers/search#!/?keyword={query}",
    "Rivian":       "https://rivian.com/careers/search#{query}",
    "Waymo":        "https://waymo.com/joinus/#{query}",
    "Cruise":       "https://getcruise.com/careers/jobs?search={query}",
    "Lyft":         "https://www.lyft.com/careers#{query}",
    "Goldman Sachs":"https://higher.gs.com/roles?search={query}",
    "JPMorgan":     "https://jobs.jpmorganchase.com/careers?search={query}",
    "Morgan Stanley":"https://morganstanley.tal.net/vx/lang-en-GB/mobile-0/brand-2/candidate/jobboard/vacancy/1/adv/?ftq={query}",
    "BlackRock":    "https://careers.blackrock.com/en-US/jobs?search={query}",
    "Citadel":      "https://www.citadel.com/careers/open-opportunities/students/#{query}",
    "Jane Street":  "https://www.janestreet.com/join-jane-street/open-roles/#{query}",
    "Two Sigma":    "https://www.twosigma.com/careers/#{query}",
    "Ramp":         "https://ramp.com/careers#{query}",
    "Retool":       "https://retool.com/careers#{query}",
    "Airtable":     "https://airtable.com/careers#{query}",
    "Webflow":      "https://webflow.com/careers#{query}",
    "Linear":       "https://linear.app/careers#{query}",
    "Loom":         "https://www.loom.com/careers#{query}",
}

def scrape_company_careers(company, careers_url, query, max_results=3):
    listings = []
    url = careers_url.format(query=requests.utils.quote(query))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        job_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if not text or len(text) < 5:
                continue
            keywords = ["engineer", "developer", "backend", "software", "python", "data", "infrastructure"]
            if any(k in text.lower() for k in keywords):
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    base = urlparse(url)
                    href = f"{base.scheme}://{base.netloc}{href}"
                if href.startswith("http"):
                    job_links.append((text, href))
        for title, job_url in job_links[:max_results]:
            listings.append(JobListing(
                title=title,
                company=company,
                location="See job page",
                job_url=job_url,
                job_board="company_careers",
                jd_text=""
            ))
    except Exception as e:
        print(f"  Error scraping {company}: {e}")
    return listings

def fetch_jd_from_url(job_url):
    try:
        resp = requests.get(job_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in ["article", "main", "section"]:
            el = soup.find(tag)
            if el and len(el.get_text(strip=True)) > 200:
                return el.get_text(separator="\n", strip=True)[:2000]
        return soup.get_text(separator="\n", strip=True)[:2000]
    except Exception:
        return ""

def scrape_fortune500_jobs(jobs_per_day=30):
    all_listings = []
    per_company = max(1, jobs_per_day // len(FORTUNE500_CAREERS))
    query = JOB_SEARCH_QUERIES[0]
    for company, careers_url in FORTUNE500_CAREERS.items():
        print(f"  Scraping {company}...")
        listings = scrape_company_careers(company, careers_url, query, max_results=per_company)
        for job in listings:
            if not job.jd_text:
                job.jd_text = fetch_jd_from_url(job.job_url)
                time.sleep(random.uniform(1, 2))
        all_listings.extend(listings)
        time.sleep(random.uniform(1, 3))
        if len(all_listings) >= jobs_per_day:
            break
    print(f"\nTotal Fortune 500 jobs found: {len(all_listings)}")
    return all_listings


if __name__ == "__main__":
    jobs = scrape_fortune500_jobs(jobs_per_day=10)
    for j in jobs[:5]:
        print(f"\n{j.title} @ {j.company}")
        print(f"URL: {j.job_url}")
        print(f"JD: {j.jd_text[:150]}")
