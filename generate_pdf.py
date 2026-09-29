from playwright.sync_api import sync_playwright
import os
import shutil

html_path = os.path.abspath('MINE_X_COMPLETE_SYSTEM_REPORT.html')
pdf_workspace = os.path.abspath('MINE_X_COMPLETE_SYSTEM_REPORT.pdf')
pdf_artifact = r'C:\Users\Dhaksith.S\.gemini\antigravity-ide\brain\a315ed42-c692-47c0-8727-e8fd6ac52f93\MINE_X_COMPLETE_SYSTEM_REPORT.pdf'

uri = 'file:///' + html_path.replace('\\', '/')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(uri, wait_until='networkidle')
    page.pdf(path=pdf_workspace, format='A4', print_background=True, margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
    shutil.copyfile(pdf_workspace, pdf_artifact)
    browser.close()

print('PDF exported successfully to:', pdf_workspace)
print('PDF exported successfully to:', pdf_artifact)
