import json
from pathlib import Path

def main():
    # 仮のスクレイピングデータ
    scraped_data = [
        {"title": "はじめての自動収集記事 1", "url": "https://example.com/1", "date": "2026-06-07"},
        {"title": "はじめての自動収集記事 2", "url": "https://example.com/2", "date": "2026-06-07"}
    ]

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
