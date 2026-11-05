from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import asyncio

app = FastAPI(title="Playwright Crawler API")

class ScrapeRequest(BaseModel):
    url: HttpUrl

class ScrapeResponse(BaseModel):
    url: str
    title: str
    description: str
    headings: list[str]

@app.get("/")
async def health_check():
    return {"status": "active", "message": "Crawler API is running live on Render"}

@app.post("/extract", response_model=ScrapeResponse)
async def extract_content(request: ScrapeRequest):
    url = str(request.url)

    try:
        async with async_playwright() as p:
            # Launch browser with optimized flags for container environments
            browser = await p.chromium.launch(
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )

            # Use a context to apply stealth and resource blocking
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = await context.new_page()

            # Anti-Bot Stealth
            await stealth_async(page)

            # Memory Optimization: Block images, media, fonts, and stylesheets
            async def block_resources(route):
                resource_type = route.request.resource_type
                if resource_type in ["image", "media", "font", "stylesheet"]:
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", block_resources)

            try:
                # Navigate with a timeout to prevent hanging processes
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Data Extraction
                title = await page.title()

                # Extract meta description
                description = await page.locator('meta[name="description"]').get_attribute("content") or \
                              await page.locator('meta[property="og:description"]').get_attribute("content") or \
                              "No description found"

                # Extract all H2 headings
                h2_elements = await page.locator("h2").all_text_contents()

                return ScrapeResponse(
                    url=url,
                    title=title,
                    description=description,
                    headings=h2_elements
                )

            except asyncio.TimeoutError:
                raise HTTPException(status_code=408, detail="Request timed out while scraping the page")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")
            finally:
                await browser.close()

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/scrape")
async def scrape_url(url: str):
    # Kept for backward compatibility, but /extract is recommended
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = await browser.new_page()
        await page.goto(url)
        title = await page.title()
        await browser.close()
        return {"url": url, "page_title": title}
