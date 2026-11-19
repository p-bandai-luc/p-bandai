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
                            # クッキークリア＆ランダムウェイト
                            context.clear_cookies()
                            sleep_sec = random.uniform(3.0, 5.0)
                            page.wait_for_timeout(int(sleep_sec * 1000))

                            # 詳細ページへ移動
                            page.goto(item_url, timeout=30000)
                            page.wait_for_timeout(3000)

                            # ページを少しスクロールして確実に描画させる
                            page.evaluate("window.scrollBy(0, 400)")
                            page.wait_for_timeout(1500)

                            # ページ内のJavaScript変数やDOMから注文番号と最大数量を同時に安全抽出
                            extracted = page.evaluate("""() => {
                                let oNo = "";
                                let mQty = 1;

                                // 1. orderno_list から注文番号を取得
                                try {
                                    if (typeof orderno_list !== 'undefined') {
                                        for (let key in orderno_list) {
                                            let val = orderno_list[key];
                                            if (typeof val === 'string' && val.length >= 7 && /^\d+$/.test(val)) {
                                                oNo = val;
                                                break;
                                            }
                                        }
                                    }
                                } catch (e) {}

                                // 2. ページ内の隠しinput等からもフォールバック検索
                                if (!oNo) {
                                    const inputs = document.querySelectorAll('input[name*="order"], input[type="hidden"]');
                                    for (let input of inputs) {
                                        let val = input.value;
                                        if (val && val.length >= 7 && /^\d+$/.test(val)) {
                                            oNo = val;
                                            break;
                                        }
                                    }
                                }

                                // 3. #unit セレクトボックスから最大購入数を取得
                                const select = document.querySelector('#unit');
                                if (select) {
                                    for (let option of select.options) {
                                        const val = parseInt(option.value, 10);
                                        if (!isNaN(val) && val > mQty) {
                                            mQty = val;
                                        }
                                    }
                                }

                                // 4. ordermax_list からのフォールバック
                                try {
                                    if (typeof ordermax_list !== 'undefined') {
                                        for (let key in ordermax_list) {
                                            let val = parseInt(ordermax_list[key], 10);
                                            if (!isNaN(val) && val > mQty) {
                                                mQty = val;
                                            }
                                        }
                                    }
                                } catch (e) {}

                                return { orderNo: oNo, max: mQty };
                            }""")

                            order_no = extracted.get("orderNo", "")
                            max_val = extracted.get("max", 1)

                            print(f"  -> orderNo: {order_no}, max: {max_val}")

                            # 次のループのために一覧ページへ戻る
                            page.goto(TARGET_URL, timeout=30000)
                            page.wait_for_timeout(2000)

                        except Exception as e:
                            print(f"  Error fetching detail page: {e}")
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
