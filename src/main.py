from fastapi import FastAPI
from playwright.async_api import async_playwright

app = FastAPI(title="Playwright Crawler API")

@app.get("/")
async def health_check():
    return {"status": "active", "message": "Crawler API is running live on Render"}

@app.get("/scrape")
async def scrape_url(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = await browser.new_page()
        await page.goto(url)
        title = await page.title()
        await browser.close()
        return {"url": url, "page_title": title}
