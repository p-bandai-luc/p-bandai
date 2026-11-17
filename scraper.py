import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL = "https://p-bandai.jp/chara/c0010/?q=&q2=&C1=c0010&C2=S0004&C3=&C4=&C5=&C6=&C7=&C8=&p=&c=60&sort=1&exact_dictionary_list=&page=1&search_on_flg=1&select_sc=&op_sf=0&op_cate=&op_cname=&op_ckana="

def main():
    scraped_data = []
    jst = timezone(timedelta(hours=+9), 'JST')
    now_str = datetime.now(jst).strftime('%Y-%m-%d %H:%M')

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
            page.wait_for_timeout(5000)
            
            # ページ内の商品カード（または商品名が含まれそうな要素）を広く探す
            # プレバンの商品名やリンクになりそうなアンカータグをすべて抽出
            links = page.locator('a[href*="/item/"]').all()
            print(f"Found {len(links)} links containing '/item/'")

            for i, link in enumerate(links[:15]): # 最初の15件をログに出力して中身を確認
                href = link.get_attribute("href")
                text = link.inner_text().strip()
                print(f"--- Link {i+1} ---")
                print(f"HREF: {href}")
                print(f"TEXT:\n{text}\n")

        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            browser.close()

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
