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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="ja-JP"
        )
        page = context.new_page()
        
        try:
            print(f"Accessing URL: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            html_content = page.content()
            match = re.search(r'const\s+ga_items\s*=\s*(\[.*?\]);', html_content, re.DOTALL)
            
            if match:
                ga_items_str = match.group(1)
                try:
                    ga_items = json.loads(ga_items_str)
                except Exception:
                    import ast
                    ga_items = ast.literal_eval(ga_items_str.replace('null', 'None').replace('true', 'True').replace('false', 'False'))
                
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
