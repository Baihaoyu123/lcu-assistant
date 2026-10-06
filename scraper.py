import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json, time, os, re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

SITES = [
    {"name": "物信学院", "url": "https://phys.lcu.edu.cn", "paths": ["/xwzx/zxdt/index.htm", "/xwzx/tzgg.htm"]},
    {"name": "研究生招生网", "url": "https://yz.lcu.edu.cn", "paths": ["/zsdt/index.htm"]},
    {"name": "教务处", "url": "https://jwc.lcu.edu.cn", "paths": ["/tzgg.htm"]},
    {"name": "创新创业学院", "url": "https://cxcy.lcu.edu.cn", "paths": ["/tzgg.htm"]}
]

KEYWORDS = {
    "保研": ["推免", "保研", "免试", "推荐免试"],
    "考研": ["考研", "硕士招生", "复试", "调剂", "初试", "录取", "招生简章"],
    "竞赛": ["竞赛", "电子设计", "挑战杯", "互联网+", "数学建模", "创新创业", "大唐杯"],
    "考试": ["考试", "考核", "四六级", "期中", "期末", "学业预警"],
    "政策": ["管理办法", "实施细则", "规定", "章程", "通知", "转专业", "培养方案"]
}

def fetch(url, retries=2):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception as e:
            if i == retries - 1: print(f"  [失败] {url} — {e}")
            time.sleep(1)
    return None

def classify(text):
    return [tag for tag, words in KEYWORDS.items() if any(w in text for w in words)]

def extract_date(text):
    patterns = [r"(\d{4})-(\d{2})-(\d{2})", r"(\d{4})年(\d{1,2})月(\d{1,2})日", r"(\d{4})\.(\d{1,2})\.(\d{1,2})"]
    for p in patterns:
        m = re.search(p, text)
        if m:
            y, mo, d = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
    return datetime.now().strftime("%Y-%m-%d")

def crawl_site(site):
    results = []
    for path in site["paths"]:
        list_url = urljoin(site["url"], path)
        print(f"\n正在抓取: {site['name']} → {list_url}")
        html = fetch(list_url)
        if not html: continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href, title = a.get("href", ""), a.get_text(strip=True)
            if not title or len(title) < 6: continue
            if any(x in href for x in ["javascript", "#", "mailto", "index.htm"]): continue
            full_url = urljoin(list_url, href)
            if not full_url.startswith("http"): continue
            if any(x in full_url.lower() for x in [".jpg", ".png", ".css", ".js", ".zip"]): continue
            tags = classify(title)
            if tags:
                date = extract_date((a.parent.get_text(strip=True) if a.parent else "") + " " + title)
                results.append({"source": site["name"], "title": title, "url": full_url, "tags": tags, "date": date})
                print(f"  [{','.join(tags)}] {title}")
        time.sleep(1)
    return results

def main():
    all_results = []
    for site in SITES:
        all_results.extend(crawl_site(site))
    
    if len(all_results) < 3:
        print(f"⚠️ 只抓到 {len(all_results)} 条，拒绝写入。")
        return

    os.makedirs("data", exist_ok=True)
    data_file = os.path.join("data", "documents.json")
    
    existing = []
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f: existing = json.load(f)
        except: pass
    
    seen = {item["url"] for item in all_results}
    for item in existing:
        if item["url"] not in seen: all_results.append(item)
    
    all_results.sort(key=lambda x: x.get("date", "0000-00-00"), reverse=True)
    
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 本次抓取 {len(all_results)} 条，已保存至 {data_file}")

if __name__ == "__main__":
    main()
