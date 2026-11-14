"""Streamlit Community Cloud 앱이 잠들지 않도록 실제 브라우저로 방문해요. (GitHub Actions에서 6시간마다 실행)

- 앱은 12시간 동안 방문이 없으면 잠들어요. 그 전에 방문해서 깨어 있게 해요.
- 이미 잠들어 있으면 "Yes, get this app back up!" 버튼을 눌러 깨워요.
- 환자 이름을 입력하지 않으므로 환자 기록은 만들지 않아요.
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

URL = os.environ.get("APP_URL", "https://maeumi-mdd.streamlit.app/")
WAKE_TEXT = "Yes, get this app back up!"


def app_loaded(page):
    """앱 화면(iframe 안의 Streamlit 앱)에 마음이 첫 화면 글자가 보이면 성공"""
    for frame in page.frames:
        try:
            if "마음이" in frame.inner_text("body", timeout=2000):
                return True
        except Exception:
            continue
    return False


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_timeout(8_000)

    wake = page.get_by_role("button", name=WAKE_TEXT)
    if wake.count():
        print("앱이 잠들어 있어 깨우는 중...")
        wake.first.click()

    deadline = time.time() + 240
    while time.time() < deadline:
        if app_loaded(page):
            print(f"앱이 열렸어요: {URL}")
            browser.close()
            sys.exit(0)
        page.wait_for_timeout(5_000)

    print("4분 안에 앱이 열리지 않았어요. Streamlit 앱 상태를 확인해 주세요.")
    browser.close()
    sys.exit(1)
