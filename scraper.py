import json
import random
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL = "https://p-bandai.jp/chara/c0010/?q=&q2=&C1=c0010&C2=S0004%2CS0075&C3=&C4=&C5=&C6=&C7=&C8=&p=&c=60&sort=1&exact_dictionary_list=&page=1&search_on_flg=1&select_sc=&op_sf=0&op_cate=&op_cname=&op_ckana="

def main():
    scraped_data = []
    jst = timezone(timedelta(hours=+9), 'JST')
    now_str = datetime.now(jst).strftime('%Y-%m-%d %H:%M')

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
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
        
        # 1つのタブ（ページ）だけで最初から最後まで処理する
        page = context.new_page()
        
        try:
            print(f"Accessing URL: {TARGET_URL}")
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_timeout(5000)

            # 一覧ページから ga_items を取得
            ga_items = page.evaluate("typeof ga_items !== 'undefined' ? ga_items : null")
            
            if ga_items and isinstance(ga_items, list):
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
                        print(f"[{index}/10] Processing: {clean_name}")
                        try:
                            # 個別ページに行く前にキャッシュやクッキーをクリアして綺麗にする
                            context.clear_cookies()
                            
                            # ランダムなウェート
                            sleep_sec = random.uniform(5.0, 8.0)
                            print(f"  Waiting {sleep_sec:.1f}s...")
                            page.wait_for_timeout(int(sleep_sec * 1000))

                            # 新しいタブを開かず、既存のページで直接リンク先に移動する
                            page.goto(item_url, timeout=30000)
                            page.wait_for_timeout(3000)

                            # 人間らしい動きを模倣
                            page.evaluate("window.scrollBy(0, 400)")
                            page.wait_for_timeout(1500)

                            # セレクトボックス（#unit）から最大購入数を正確に抽出（堅牢化版）
                            try:
                                page.wait_for_selector("#unit", timeout=20000)
                            except:
                                pass # #unit が無いページ（在庫なし等）の場合はスルー

                            max_val = page.evaluate("""() => {
                                const select = document.querySelector('#unit');
                                if (!select) return 1;

                                let maxQty = 1;
                                for (let option of select.options) {
                                    const val = parseInt(option.value, 10);
                                    if (!isNaN(val) && val > maxQty) {
                                        maxQty = val;
                                    }
                                }
                                return maxQty;
                            }""")

                            # orderno_list 取得
                            orderno_list = page.evaluate("typeof orderno_list !== 'undefined' ? orderno_list : null")
                            if orderno_list and isinstance(orderno_list, dict):
                                order_no = orderno_list.get("0000000000", "")

                            # 次のループのために一覧ページへ戻る
                            page.goto(TARGET_URL, timeout=30000)
                            page.wait_for_timeout(3000)

                        except Exception as e:
                            print(f"  Error fetching detail page: {e}")
                            # エラーが起きた場合も一覧ページに戻して復帰を試みる
                            try:
                                page.goto(TARGET_URL, timeout=30000)
                            except:
                                pass

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
