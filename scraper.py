import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

TARGET_URL = "https://p-bandai.jp/chara/c0010/?q=&q2=&C1=c0010&C2=S0004&C3=&C4=&C5=&C6=&C7=&C8=&p=&c=60&sort=1&exact_dictionary_list=&page=1&search_on_flg=1&select_sc=&op_sf=0&op_cate=&op_cname=&op_ckana="

def main():
    scraped_data = []
    jst = timezone(timedelta(hours=+9), 'JST')
    now_str = datetime.now(jst).strftime('%Y-%m-%d %H:%M')

    api_key = os.environ.get("SCRAPER_API_KEY")
    if not api_key:
        print("Error: SCRAPER_API_KEY is not set.")
        return

    # ScraperAPI経由でリクエストを送る（render=trueを指定してJSをレンダリングさせる）
    payload = {
        'api_key': api_key,
        'url': TARGET_URL,
        'render': 'true',
        'country_code': 'jp' # 日本のIPを指定
    }
    
    print("Requesting via ScraperAPI...")
    response = requests.get('https://api.scraperapi.com/', params=payload, timeout=90)
    
    if response.status_code != 200:
        print(f"Failed to fetch page. Status code: {response.status_code}")
        return

    html_content = response.text
    print(f"Successfully fetched HTML length: {len(html_content)}")

    # HTMLの中から const ga_items = [...] の配列部分を抽出
    match = re.search(r'const\s+ga_items\s*=\s*(\[.*?\]);', html_content, re.DOTALL)
    
    if match:
        ga_items_str = match.group(1)
        try:
            ga_items = json.loads(ga_items_str)
        except Exception:
            import ast
            ga_items = ast.literal_eval(ga_items_str.replace('null', 'None').replace('true', 'True').replace('false', 'False'))
        
        print(f"Successfully extracted {len(ga_items)} items from data.")

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
        print("Could not find ga_items in the fetched content.")

    # data/data.json に保存
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully saved {len(scraped_data)} items to data.json")

if __name__ == "__main__":
    main()
