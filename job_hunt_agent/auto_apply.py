import asyncio
import os
from playwright.async_api import async_playwright
from config import YOUR_NAME, YOUR_EMAIL

os.makedirs("screenshots", exist_ok=True)

async def apply_company_site(page, job_url, company, resume_path):
    try:
        await page.goto(job_url, timeout=30000)
        await page.wait_for_timeout(3000)

        apply_selectors = [
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply for this job')",
            "button:has-text('Apply for this job')",
            "a:has-text('Apply for this position')",
            "button:has-text('Apply')",
            "a:has-text('Apply')",
        ]

        clicked = False
        for selector in apply_selectors:
            btn = page.locator(selector).first
            if await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(2000)
                clicked = True
                print(f"    Clicked Apply button")
                break

        if not clicked:
            print(f"    No Apply button found — saving screenshot")
            path = f"screenshots/{company.replace(' ','_')}_manual.png"
            await page.screenshot(path=path, full_page=True)
            return False

        # Fill name
        for sel in ["input[name*='full'][name*='name']", "input[placeholder*='Full name']", "input[id*='fullName']", "input[name='name']"]:
            field = page.locator(sel).first
            if await field.is_visible():
                await field.fill(YOUR_NAME)
                break

        # Fill email
        email_field = page.locator("input[type='email']").first
        if await email_field.is_visible():
            await email_field.fill(YOUR_EMAIL)

        # Fill phone
        phone_field = page.locator("input[type='tel'], input[name*='phone']").first
        if await phone_field.is_visible():
            await phone_field.fill("+15105163404")

        # Upload resume
        file_input = page.locator("input[type='file']").first
        if await file_input.is_visible():
            await file_input.set_input_files(resume_path)
            await page.wait_for_timeout(1000)
            print(f"    Resume uploaded")

        # Screenshot for review
        path = f"screenshots/{company.replace(' ','_')}_filled.png"
        await page.screenshot(path=path, full_page=True)
        print(f"    Form filled — screenshot saved: {path}")
        print(f"    Open screenshot to review, then submit manually if needed")
        return True

    except Exception as e:
        print(f"    Error: {e}")
        return False

async def auto_apply(job_url, job_board, company, resume_path, headless=False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        success = await apply_company_site(page, job_url, company, resume_path)
        await browser.close()
        return success

def run_auto_apply(job_url, job_board, company, resume_path, headless=False):
    return asyncio.run(auto_apply(job_url, job_board, company, resume_path, headless))

if __name__ == "__main__":
    import os
    # Find a real tailored resume
    resumes = os.listdir("tailored_resumes")
    stripe_resume = next((r for r in resumes if "Stripe" in r), resumes[0] if resumes else None)
    if stripe_resume:
        resume_path = f"tailored_resumes/{stripe_resume}"
        print(f"Testing with resume: {stripe_resume}")
        result = run_auto_apply(
            job_url="https://stripe.com/jobs/listing/software-engineer-bridge/6044648",
            job_board="company_careers",
            company="Stripe",
            resume_path=resume_path,
            headless=False
        )
        print(f"Result: {result}")
    else:
        print("No resumes found — run apply_loop.py first")
