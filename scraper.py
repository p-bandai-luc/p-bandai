import json
import os
import random
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# ご指定の検索・絞り込み済みURLを設定
TARGET_URL = "https://p-bandai.jp/chara/c0010/?q=&q2=&C1=c0010&C2=S0004%2CS0075&C3=&C4=&C5=&C6=&C7=&C8=&p=&c=60&sort=1&exact_dictionary_list=&page=1&search_on_flg=1&select_sc=&op_sf=0&op_cate=&op_cname=&op_ckana="

def scrape_p_bandai():
    data_list = []
    
    with sync_playwright() as p:
        # ブラウザを起動（headless=True で完全に裏で実行）
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--start-maximized"
            ]
        )
        
        # ボット検知を避けるためのUser-Agentやビューポートの設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        print("一覧ページにアクセス中...")
        try:
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"[警告] 一覧ページのロード待機タイムアウト（続行します）: {e}")
            
        # 人間らしいスクロール動作のシミュレーション
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
        time.sleep(random.uniform(2.0, 4.0))
        
        # トップ10の商品要素を取得
        item_elements = page.query_selector_all(".itemBox, .item-box, .c-item-box, li.item, .elg-itemBox")
        
        # もし特定の共通クラスで取れない場合のフォールバック（リンク構造からの抽出）
        if not item_elements:
            print("標準セレクタでの取得ができなかったため、商品リンクから抽出を試みます...")
            links = page.query_selector_all("a[href*='/item/item-']")
            seen_urls = set()
            target_items = []
            
            for link in links:
                href = link.get_attribute("href")
                if href and "/item/item-" in href:
                    if not href.startswith("http"):
                        href = "https://p-bandai.jp" + href
                    clean_url = href.split("?")[0].split("#")[0]
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        title = link.inner_text().strip()
                        if not title:
                            title = "名称不明"
                        target_items.append({"url": clean_url, "title": title})
                        if len(target_items) >= 10:
                            break
            items_to_process = target_items
        else:
            items_to_process = []
            for el in item_elements[:10]:
                title_el = el.query_selector("a, .item-title, .title")
                link_el = el.query_selector("a[href*='/item/item-']")
                price_el = el.query_selector(".price, .item-price, .value")
                
                url = link_el.get_attribute("href") if link_el else ""
                if url and not url.startswith("http"):
                    url = "https://p-bandai.jp" + url
                
                title = title_el.inner_text().strip() if title_el else "名称不明"
                price = price_el.inner_text().strip() if price_el else ""
                
                if url:
                    items_to_process.append({"url": url, "title": title, "price": price})

        print(f"対象アイテム数: {len(items_to_process)}件。詳細ページを解析します...")
        
        # 各商品の詳細ページを巡回
        for idx, item in enumerate(items_to_process[:10], 1):
            item_url = item["url"]
            title = item.get("title", "名称不明")
            price = item.get("price", "")
            
            print(f"[{idx}/10] 解析中: {title}")
            
            order_no = ""
            max_qty = 1
            
            try:
                # WAFブロック回避のため、ページ移動前にCookieをクリア
                context.clear_cookies()
                
                page.goto(item_url, timeout=60000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                
                # 人間らしいランダムなウェイト (6〜10秒)
                sleep_sec = random.uniform(6.0, 10.0)
                time.sleep(sleep_sec)
                
                # 注文番号およびセレクトボックスからの正確な最大数量の抽出
                extracted_data = page.evaluate("""() => {
                    let oNo = "";
                    let mQty = 1;

                    // 1. orderno_list 変数から注文番号を取得
                    try {
                        if (typeof orderno_list !== 'undefined') {
                            for (let key in orderno_list) {
                                let val = orderno_list[key];
                                if (typeof val === 'string' && val.length > 5 && !val.includes('http')) {
                                    oNo = val;
                                    break;
                                }
                            }
                        }
                    } catch (e) {}

                    // 2. DOM内から orderNo に該当しそうな文字列やinput要素を探す
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

                    // 3. #unit セレクトボックスのオプションから最大購入数を正確に抽出
                    const select = document.querySelector('#unit');
                    if (select) {
                        for (let option of select.options) {
                            const val = parseInt(option.value, 10);
                            if (!isNaN(val) && val > mQty) {
                                mQty = val;
                            }
                        }
                    }

                    return { orderNo: oNo, max: mQty };
                }""")
                
                order_no = extracted_data.get("orderNo", "")
                max_qty = extracted_data.get("max", 1)
                
            except Exception as e:
                print(f"[エラー] 詳細ページの取得に失敗 ({item_url}): {e}")

            # 価格が空だった場合のフォールバック抽出
            if not price:
                try:
                    price_element = page.query_selector(".price, .item-price, .sellingPrice")
                    if price_element:
                        price = price_element.inner_text().strip()
                except Exception:
                    pass

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            data_list.append({
                "title": title.replace("\n", " "),
                "price": price,
                "item_url": item_url,
                "orderNo": order_no,
                "max": max_qty,
                "date": current_time
            })
            
        browser.close()

    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)
    
    # data.json として保存
    file_path = "data/data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
        
    print(f"スクレイピング完了！データを {file_path} に保存しました。")

if __name__ == "__main__":
    scrape_p_bandai()
