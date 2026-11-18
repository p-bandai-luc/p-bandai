import json
import random
import re
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
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--start-maximized"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
            java_script_enabled=True
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()
        
        try:
            print(f"Accessing URL: {TARGET_URL}")
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_timeout(5000)

            # 一覧ページから ga_items を取得
            ga_items = page.evaluate("typeof ga_items !== 'undefined' ? ga_items : null")
            
            if ga_items and isinstance(ga_items, list):
                # 最新10件に限定
                target_items = ga_items[:10]
                print(f"Found {len(ga_items)} items total. Processing top {len(target_items)} items...")

                for index, item in enumerate(target_items, 1):
                    raw_name = item.get("item_name", "")
                    clean_name = re.sub(r'^\d+_', '', raw_name)
                    item_url = item.get("item_category5", "")
                    
                    price_val = item.get("price", "")
                    price_str = f"¥{int(price_val):,}" if str(price_val).isdigit() else price_val

                    order_no = ""
                    max_val = 1

                    if item_url:
                        print(f"[{index}/10] Visiting detail page: {clean_name}")
                        try:
                            # ★ 連続アクセスによるブロックを防ぐため、3秒〜6秒のランダムなウェートを入れる
                            sleep_sec = random.uniform(3.0, 6.0)
                            page.wait_for_timeout(int(sleep_sec * 1000))

                            page.goto(item_url, timeout=30000)
                            page.wait_for_timeout(2000)

                            # ★ 人間らしい動作を模倣して少しスクロールする
                            page.evaluate("window.scrollBy(0, 300)")
                            page.wait_for_timeout(1500)

                            # orderno_list から "0000000000" に対応する orderNo を取得
                            orderno_list = page.evaluate("typeof orderno_list !== 'undefined' ? orderno_list : null")
                            if orderno_list and isinstance(orderno_list, dict):
                                order_no = orderno_list.get("0000000000", "")

                            # セレクトボックス (#unit) から最大値 (max) を取得
                            options = page.eval_on_selector_all("#unit option", "elements => elements.map(e => e.value)")
                            valid_qtys = [int(val) for val in options if val.isdigit() and int(val) > 0]
                            if valid_qtys:
                                max_val = max(valid_qtys)

                        except Exception as e:
                            print(f"  Error fetching detail page: {e}")

                    # 必要なデータ構造のみ保持
                    scraped_data.append({
                        "title": clean_name,
                        "price": price_str,
                        "item_url": item_url,
                        "orderNo": order_no,
                        "max": max_val,
                        "date": now_str
                    })
            else:
                print("ga_items is not defined.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(scraped_data)} items to data.json")

if __name__ == "__main__":
    main()
