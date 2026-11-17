import json
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
        
        captured_html = ""

        # レスポンスを監視し、目的のURLからのXHRレスポンス（HTML）をキャッチする
        def handle_response(response):
            nonlocal captured_html
            if "/chara/c0010" in response.url and response.request.resource_type in ["document", "fetch", "xhr"]:
                text = response.text()
                if "ga_items" in text:  # ga_itemsが含まれているレスポンスを狙う
                    captured_html = text

        page.on("response", handle_response)
        
        try:
            print(f"Accessing URL: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000) # 非同期の通信完了を少し待つ

            # もしイベントでキャッチできていなければ、現在のページのコンテンツを取得
            if not captured_html:
                captured_html = page.content()

            # キャッチしたHTMLテキストの中から const ga_items = [...] の配列部分を正規表現で抜き出す
            match = re.search(r'const\s+ga_items\s*=\s*(\[.*?\]);', captured_html, re.DOTALL)
            
            if match:
                ga_items_str = match.group(1)
                # JavaScriptの配列文字列をPythonのリストに変換（シングルクォートやエスケープの調整が必要な場合があるため安全に処理）
                # プレバンの出力はダブルクォートの標準的なJSONに近い形なのでそのままパースを試みる
                try:
                    ga_items = json.loads(ga_items_str)
                except Exception:
                    # うまくいかない場合は簡易的に評価
                    import ast
                    ga_items = ast.literal_eval(ga_items_str.replace('null', 'None').replace('true', 'True').replace('false', 'False'))
                
                print(f"Successfully extracted {len(ga_items)} items from captured data.")

                # 上位10件を抽出
                for item in ga_items[:10]:
                    raw_name = item.get("item_name", "")
                    clean_name = re.sub(r'^\d+_', '', raw_name)
                    
                    price_val = item.get("price", "")
                    price_str = f"¥{int(price_val):,}" if str(price_val).isdigit() else price_val
                    
                    url = item.get("item_category5", "")

                    scraped_data.append({
                        "title": clean_name,
                        "price": price_str,
                        "url": url,
                        "date": now_str
                    })
            else:
                print("Could not find ga_items in the captured response.")

        except Exception as e:
            print(f"Error during extraction: {e}")
        finally:
            browser.close()

    # data/data.json に保存
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully saved {len(scraped_data)} items to data.json")

if __name__ == "__main__":
    main()
