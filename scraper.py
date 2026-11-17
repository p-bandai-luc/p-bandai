import json
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL = "https://p-bandai.jp/chara/c0010/?q=&q2=&C1=c0010&C2=S0004&C3=&C4=&C5=&C6=&C7=&C8=&p=&c=60&sort=1&exact_dictionary_list=&page=1&search_on_flg=1&select_sc=&op_sf=0&op_cate=&op_cname=&op_ckana="

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ja-JP"
        )
        page = context.new_page()
        
        try:
            print(f"Accessing URL: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(8000) # 多めに待機

            # ページのタイトルとURLを出力
            print(f"Current Page Title: {page.title()}")
            print(f"Current URL: {page.url}")

            # ページ内のテキストの一部をログに出力して何が返されているか確認
            body_text = page.inner_text("body")
            print(f"Body text length: {len(body_text)}")
            print("--- First 500 chars of body ---")
            print(body_text[:500])

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
