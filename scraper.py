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
        # ヘッドレスモードをオフ（または自動検知対策を強めたコンテキスト）で起動
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        # 一般的なPCブラウザに見せかける設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="ja-JP"
        )
        
        page = context.new_page()
        
        try:
            # ページにアクセス
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            
            # 人間のように少し待機し、スクロール動作を入れる
            page.wait_for_timeout(5000)
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(2000)

            # 商品リンクを取得
            links = page.locator('a[href*="/item/item-"]').all()
            
            seen_urls = set()
            for link in links:
                href = link.get_attribute("href")
                if not href:
                    continue
                
                full_url = f"https://p-bandai.jp{href}" if href.startswith("/") else href
                clean_url = full_url.split("?")[0]
                
                if clean_url in seen_urls:
                    continue

                text = link.inner_text().strip()
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                if not lines:
                    continue
                    
                title = lines[0]
                price = ""
                for line in lines:
                    if "円" in line or "￥" in line or "¥" in line:
                        price = line
                        break

                seen_urls.add(clean_url)
                scraped_data.append({
                    "title": title,
                    "price": price,
                    "url": clean_url,
                    "date": now_str
                })

                if len(scraped_data) >= 10:
                    break
        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            browser.close()

    # 取得できた場合のみ（または空でも）保存
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
