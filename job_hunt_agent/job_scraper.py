import requests
from bs4 import BeautifulSoup
import time
import random
from dataclasses import dataclass
from typing import List
from config import JOB_SEARCH_QUERIES, JOB_LOCATION

@dataclass
class JobListing:
    title: str
    company: str
    location: str
    job_url: str
    job_board: str
    jd_text: str = ""


EXCLUDE_TITLES = [
    "staff", "principal", "senior staff", "distinguished", "fellow",
    "director", "vp ", "vice president", "head of", "manager",
    "l5", "l6", "l7", "level 5", "level 6", "level 7",
    "senior engineer", "sr engineer", "sr. engineer",
]

INCLUDE_TITLES = [
    "software engineer", "backend engineer", "sde", "sde1", "sde2",
    "ai engineer", "ml engineer", "platform engineer", "python engineer",
    "distributed systems", "llm engineer", "genai engineer",
    "engineer i", "engineer ii", "engineer 1", "engineer 2",
    "l3", "l4", "level 3", "level 4", "mid", "junior"
]

def is_valid_role(title):
    title_lower = title.lower()
    # Skip excluded titles
    if any(ex in title_lower for ex in EXCLUDE_TITLES):
        return False
    return True

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def scrape_linkedin(query, location, max_results=10):
    listings = []
    start = 0
    while len(listings) < max_results:
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={requests.utils.quote(query)}"
            f"&location={requests.utils.quote(location)}"
            f"&sortBy=DD&f_TPR=r86400&start={start}"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            job_cards = soup.find_all("div", class_="base-card")
            if not job_cards:
                break
            for card in job_cards:
                if len(listings) >= max_results:
                    break
                try:
                    title_el = card.find("h3", class_="base-search-card__title")
                    title = title_el.get_text(strip=True) if title_el else "Unknown"
                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    company = company_el.get_text(strip=True) if company_el else "Unknown"
                    loc_el = card.find("span", class_="job-search-card__location")
                    location_text = loc_el.get_text(strip=True) if loc_el else location
                    link_el = card.find("a", class_="base-card__full-link")
                    job_url = link_el["href"].split("?")[0] if link_el else ""
                    if job_url and title != "Unknown" and is_valid_role(title):
                        listings.append(JobListing(title=title, company=company, location=location_text, job_url=job_url, job_board="linkedin"))
                except Exception:
                    continue
            start += 25
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            print(f"LinkedIn scrape error: {e}")
            break
    return listings

def fetch_linkedin_jd(job_url):
    try:
        resp = requests.get(job_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        jd_div = soup.find("div", class_="description__text")
        if jd_div:
            return jd_div.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"  Could not fetch LinkedIn JD: {e}")
    return ""

def scrape_indeed(query, location, max_results=10):
    listings = []
    start = 0
    while len(listings) < max_results:
        url = (
            f"https://www.indeed.com/jobs"
            f"?q={requests.utils.quote(query)}"
            f"&l={requests.utils.quote(location)}"
            f"&sort=date&fromage=1&start={start}"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            job_cards = soup.find_all("div", class_="job_seen_beacon")
            if not job_cards:
                break
            for card in job_cards:
                if len(listings) >= max_results:
                    break
                try:
                    title_el = card.find("h2", class_="jobTitle")
                    title = title_el.get_text(strip=True) if title_el else "Unknown"
                    company_el = card.find("span", {"data-testid": "company-name"})
                    company = company_el.get_text(strip=True) if company_el else "Unknown"
                    loc_el = card.find("div", {"data-testid": "text-location"})
                    location_text = loc_el.get_text(strip=True) if loc_el else location
                    link_el = title_el.find("a") if title_el else None
                    job_id = link_el["data-jk"] if link_el and link_el.get("data-jk") else None
                    job_url = f"https://www.indeed.com/viewjob?jk={job_id}" if job_id else ""
                    if job_url:
                        listings.append(JobListing(title=title, company=company, location=location_text, job_url=job_url, job_board="indeed"))
                except Exception:
                    continue
            start += 10
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"Indeed scrape error: {e}")
            break
    return listings

def fetch_indeed_jd(job_url):
    try:
        resp = requests.get(job_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        jd_div = soup.find("div", id="jobDescriptionText")
        if jd_div:
            return jd_div.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"  Could not fetch JD: {e}")
    return ""

def scrape_all_jobs(jobs_per_day=30):
    all_listings = []
    per_query = max(5, jobs_per_day // len(JOB_SEARCH_QUERIES))
    for query in JOB_SEARCH_QUERIES:
        print(f"\nSearching: '{query}' in {JOB_LOCATION}")
        li = scrape_linkedin(query, JOB_LOCATION, max_results=per_query)
        print(f"  LinkedIn: {len(li)} listings")
        for job in li:
            if not job.jd_text:
                job.jd_text = fetch_linkedin_jd(job.job_url)
                time.sleep(random.uniform(1, 2))
        in_ = scrape_indeed(query, JOB_LOCATION, max_results=per_query)
        print(f"  Indeed: {len(in_)} listings")
        for job in in_:
            if not job.jd_text:
                job.jd_text = fetch_indeed_jd(job.job_url)
                time.sleep(random.uniform(1, 2))
        all_listings.extend(li)
        all_listings.extend(in_)
    print(f"\nTotal listings scraped: {len(all_listings)}")
    return all_listings

if __name__ == "__main__":
    jobs = scrape_all_jobs(jobs_per_day=30)
    for j in jobs[:5]:
        print(f"\n{j.title} @ {j.company} ({j.job_board})")
        print(f"URL: {j.job_url}")
        print(f"JD preview: {j.jd_text[:150]}")
