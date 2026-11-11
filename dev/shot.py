from playwright.sync_api import sync_playwright
import sys
with sync_playwright() as p:
    b=p.chromium.launch()
    for name,w,h in [("mobile",390,844),("desktop",1280,900)]:
        pg=b.new_page(viewport={"width":w,"height":h}, device_scale_factor=1)
        errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("file:///home/claude/dream-dashboard/dist/index.html"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"dev/{name}.png", full_page=True)
        print(name, "errors:", errs, "height:", pg.evaluate("document.body.scrollHeight"), "hscroll:", pg.evaluate("document.documentElement.scrollWidth>window.innerWidth"))
    b.close()
