import requests
from config import HUNTER_API_KEY

SKIP_DOMAINS = ["linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com"]

def find_recruiter_email(company, job_url):
    domain = _get_company_domain(company)
    if not domain:
        return None
    if HUNTER_API_KEY:
        result = _hunter_lookup(domain)
        if result:
            return result
    return None

def _get_company_domain(company):
    known = {
        "google": "google.com", "meta": "meta.com", "apple": "apple.com",
        "amazon": "amazon.com", "microsoft": "microsoft.com", "stripe": "stripe.com",
        "netflix": "netflix.com", "uber": "uber.com", "airbnb": "airbnb.com",
        "shopify": "shopify.com", "twilio": "twilio.com", "snowflake": "snowflake.com",
        "databricks": "databricks.com", "notion": "notion.so", "figma": "figma.com",
        "vercel": "vercel.com", "snap": "snap.com", "twitter": "twitter.com",
        "linkedin": "linkedin.com", "salesforce": "salesforce.com", "oracle": "oracle.com",
        "ibm": "ibm.com", "intel": "intel.com", "nvidia": "nvidia.com",
        "justworks": "justworks.com", "hebbia": "hebbia.ai", "temu": "temu.com",
        "doordash": "doordash.com", "instacart": "instacart.com", "robinhood": "robinhood.com",
        "coinbase": "coinbase.com", "palantir": "palantir.com", "openai": "openai.com",
        "anthropic": "anthropic.com", "scale": "scale.com", "github": "github.com",
        "atlassian": "atlassian.com", "datadog": "datadoghq.com", "twitch": "twitch.tv",
        "reddit": "reddit.com", "dropbox": "dropbox.com", "box": "box.com",
        "zoom": "zoom.us", "slack": "slack.com", "hubspot": "hubspot.com",
    }
    company_lower = company.lower().strip()
    for key, domain in known.items():
        if key in company_lower:
            return domain
    clean = company_lower.replace(" inc", "").replace(" corp", "").replace(" ltd", "")
    clean = clean.replace(" llc", "").replace(".", "").replace(",", "").strip()
    clean = clean.replace(" ", "")
    return f"{clean}.com"

def _hunter_lookup(domain):
    if domain in SKIP_DOMAINS:
        return None
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 5, "type": "personal"},
            timeout=10
        )
        data = resp.json()
        emails = data.get("data", {}).get("emails", [])
        priority_keywords = ["recruit", "talent", "hr", "people", "hiring", "engineer"]
        for email_obj in emails:
            position = (email_obj.get("position") or "").lower()
            if any(k in position for k in priority_keywords):
                return {
                    "name": f"{email_obj.get('first_name', '')} {email_obj.get('last_name', '')}".strip(),
                    "email": email_obj.get("value")
                }
        if emails:
            e = emails[0]
            return {
                "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                "email": e.get("value")
            }
    except Exception as ex:
        print(f"  Hunter.io error for {domain}: {ex}")
    return None

if __name__ == "__main__":
    print(find_recruiter_email("Stripe", "https://stripe.com/jobs/123"))
    print(find_recruiter_email("Google", "https://linkedin.com/jobs/123"))
    print(find_recruiter_email("Vercel", "https://vercel.com/careers"))
