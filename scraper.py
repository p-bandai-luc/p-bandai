import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL = "https://p-bandai.jp/chara/c0010/?q=&q2=&C1=c0010&C2=S0004&C3=&C4=&C5=&C6=&C7=&C8=&p=&c=60&sort=1&exact_dictionary_list=&page=1&search_on_flg=1&select_sc=&op_sf=0&op_cate=&op_cname=&op_ckana="

def main():
    scraped_data = []
    # 日本時間の現在時刻を取得
    jst = timezone(timedelta(hours=+9), 'JST')
    now_str = datetime.now(jst).strftime('%Y-%m-%d %H:%M')

    with sync_playwright() as p:
        # ブラウザを起動
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # ページにアクセスし、ネットワークが落ち着くまで待機
        page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000) # 念のため3秒待機

        # 商品詳細ページ（/item/item-）へのリンク要素を取得
        links = page.locator('a[href*="/item/item-"]').all()
        
        seen_urls = set()
        for link in links:
            href = link.get_attribute("href")
            if not href:
                continue
            
            # 相対パスの場合はフルURLに変換
            full_url = f"https://p-bandai.jp{href}" if href.startswith("/") else href
            # クエリパラメータ（?rt=など）を除去して重複判定を統一
            clean_url = full_url.split("?")[0]
            
            if clean_url in seen_urls:
                continue

            # リンク内のテキスト（商品名や価格など）を取得
            text = link.inner_text().strip()
            # 画像だけの空リンクなどを除外し、商品名があるものを抽出
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

            # 10件集まったらループ終了
            if len(scraped_data) >= 10:
                break

        browser.close()

    # data/data.json に保存
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
