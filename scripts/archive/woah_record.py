import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://wahis.woah.org/#/dashboards/qd-dashboard")
    page.get_by_role("img").click()
    page.locator("iframe").first.content_frame.locator("#wDzKLD_content > .ng-scope > .MuiGrid-root.MuiGrid-container.filter-pane-container > .MuiGrid-root.MuiGrid-item.css-d5b7l0 > .MuiBox-root > .MuiGrid-root.MuiGrid-item.css-rnbtta > .listbox-popover-container > .folded-listbox > .MuiGrid-root.MuiGrid-container.MuiGrid-direction-xs-column > .MuiGrid-root.MuiGrid-container.css-q0qbej").click()
    page.locator("iframe").first.content_frame.get_by_title("Afrique du Sud").click()
    page.get_by_role("button", name="Exporter les données").click()
    with page.expect_download() as download_info:
        page.locator("iframe").nth(1).content_frame.locator(".fa").click()
    download = download_info.value
    page.locator("iframe").nth(1).content_frame.locator("#pKMBT_content > .ng-scope > .MuiGrid-root.MuiGrid-container.filter-pane-container > .MuiGrid-root.MuiGrid-item.css-d5b7l0 > .MuiBox-root > .MuiGrid-root.MuiGrid-item.css-rnbtta > .listbox-popover-container > .folded-listbox > .MuiGrid-root.MuiGrid-container.MuiGrid-direction-xs-column > .MuiGrid-root.MuiGrid-container.css-q0qbej").click()
    page.locator("iframe").nth(1).content_frame.get_by_title("Afrique du Sud").click()
    with page.expect_download() as download1_info:
        page.locator("iframe").nth(1).content_frame.locator(".MuiBackdrop-root").click()
    download1 = download1_info.value
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
