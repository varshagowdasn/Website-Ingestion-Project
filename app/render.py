import hashlib
from playwright.async_api import async_playwright
async def render(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        for selector in ("[data-open-modal]", "[data-extract-click]"):
            buttons = page.locator(selector)
            for i in range(await buttons.count()):
                try:
                    await buttons.nth(i).click(timeout=1500)
                except Exception:
                    pass
        await page.evaluate("async()=>{let wait=ms=>new Promise(r=>setTimeout(r,ms));for(let y=0;y<document.body.scrollHeight;y+=500){window.scrollTo(0,y);await wait(60)}for(let e of document.querySelectorAll('*')){if(e.scrollHeight>e.clientHeight+30&&/auto|scroll/.test(getComputedStyle(e).overflowY)){e.scrollTop=e.scrollHeight;await wait(60)}}}")
        title = await page.title()
        text = await page.locator("body").inner_text()
        await browser.close()
    content = "\n".join(x.strip() for x in text.splitlines() if x.strip())
    return title, content, hashlib.sha256(content.encode()).hexdigest()
