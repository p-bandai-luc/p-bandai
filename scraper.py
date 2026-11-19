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
                            # キャッシュクリアとランダムウェイト
                            context.clear_cookies()
                            sleep_sec = random.uniform(3.0, 5.0)
                            page.wait_for_timeout(int(sleep_sec * 1000))

                            # XHR/レスポンスのHTMLを直接キャッチするための変数
                            fetched_html = ""

                            def handle_response(response):
                                nonlocal fetched_html
                                # 該当する商品URLへのリクエストかつステータス200のレスポンスをキャッチ
                                if item_url in response.url and response.status == 200:
                                    try:
                                        text = response.text()
                                        if "orderno_list" in text or "unit" in text:
                                            fetched_html = text
                                    except:
                                        pass

                            # レスポンスイベントリスナーを登録
                            page.on("response", handle_response)

                            # ページへ移動（これに伴うXHRレスポンスをキャッチする）
                            page.goto(item_url, timeout=30000)
                            page.wait_for_timeout(3000)

                            # リスナーを解除
                            page.remove_listener("response", handle_response)

                            # もしXHRで取れなかった場合は現在のDOMのHTMLをフォールバックとして使用
                            if not fetched_html:
                                fetched_html = page.content()

                            # --- 取得したHTML文字列から正規表現等で確実にデータを抽出 ---
                            
                            # 1. orderno_list の抽出 (例: "0000000000":"2753038000003")
                            orderno_match = re.search(r'"0000000000"\s*:\s*"(\d+)"', fetched_html)
                            if orderno_match:
                                order_no = orderno_match.group(1)

                            # 2. 数量（#unit の option の value）の抽出
                            # <select ... id="unit"...> から中の <option value="X"> をすべて探し出す
                            unit_select_match = re.search(r'<select[^>]*id=["\']unit["\'][^>]*>(.*?)</select>', fetched_html, re.DOTALL)
                            if unit_select_match:
                                options_html = unit_select_match.group(1)
                                option_values = re.findall(r'value=["\'](\d+)["\']', options_html)
                                valid_qtys = [int(v) for v in option_values if int(v) > 0]
                                if valid_qtys:
                                    max_val = max(valid_qtys)

                            # 3. フォールバック: ordermax_list からの抽出
                            if max_val == 1:
                                ordermax_match = re.search(r'ordermax_list\s*=\s*\{([^}]+)\}', fetched_html)
                                if ordermax_match:
                                    max_nums = re.findall(r':\s*(\d+)', ordermax_match.group(1))
                                    valid_nums = [int(n) for n in max_nums if int(n) > 0]
                                    if valid_nums:
                                        max_val = max(valid_nums)

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
