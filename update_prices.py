# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json
import time
import os
import re

TICKERS = [
    "139320","229200","498400","472150","441640","483320","426030",
    "491620","478150","0131V0","0040X0","0023A0","0117V0","456600",
    "490590","493810","483330","441640",
    "396500","0093A0","475300","395270","449450","490480","0080G0",
    "494670","480030","0115D0","305540","305720",
    "232080","270810","354500","261070","316670","450910","461580",
    "261060","461450","304770","301400",
    "385720","302450","292150","462330","140950","226380","152500","105190",
    "005930","000660","009150","042700","058470","240810","039030",
    "000990","403870","036930","095340","084370","357780","440110",
    "064760","005290","031980","089030","232140","095610","089970",
    "487240","010120","298040","267260","006260","001440","103590",
    "062040","033100","000500","060370","229640",
    "272210","079550","099320","189300","077970","329180","042660",
    "047810","064350","103140","003570","484870","214430","012450",
    "364980","461950","006400","005490","373220","051910",
    "086520","247540","003670","096770","450080","066970","011790",
    "020150","361610","005070","348370","121600",
]
TICKERS = list(dict.fromkeys(TICKERS))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://finance.naver.com/",
    "Accept": "application/json, text/html, */*",
}

def fetch_json(url, timeout=8):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))

def fetch_html(url, timeout=8):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("euc-kr", errors="ignore")

def parse_num(val):
    if not val:
        return 0
    return int(str(val).replace(",", "").replace("+", "").strip() or "0")

def parse_float(val):
    if not val:
        return 0.0
    return float(str(val).replace(",", "").strip() or "0")

def try_mobile_api(code):
    """m.stock.naver.com 모바일 API"""
    url = f"https://m.stock.naver.com/api/stock/{code}/basic"
    d = fetch_json(url)
    name  = d.get("stockName") or d.get("itemName") or ""
    price = parse_num(d.get("closePrice"))
    diff  = parse_num(d.get("compareToPreviousClosePrice"))
    pct   = parse_float(d.get("fluctuationsRatio"))
    if name and price:
        return {"name": name, "price": price, "diff": diff, "pct": pct}
    return None

def try_finance_api(code):
    """네이버 금융 itemSummary API"""
    url = f"https://api.finance.naver.com/service/itemSummary.nhn?itemcode={code}"
    d = fetch_json(url)
    # 이 API는 가격만 반환
    price = parse_num(d.get("now"))
    diff  = parse_num(d.get("diff"))
    pct   = parse_float(d.get("rate"))
    name  = d.get("name") or ""
    if price:
        return {"name": name, "price": price, "diff": diff, "pct": pct}
    return None

def try_sise_html(code):
    """네이버 금융 sise 페이지 HTML 스크래핑"""
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    html = fetch_html(url)
    # 종목명
    name_m = re.search(r'<title>\s*([^:]+?)\s*:', html)
    name = name_m.group(1).strip() if name_m else ""
    # 현재가
    price_m = re.search(r'id="_nowVal"[^>]*>([\d,]+)<', html)
    price = parse_num(price_m.group(1)) if price_m else 0
    # 전일대비
    diff_m = re.search(r'id="_diff"[^>]*>([\d,]+)<', html)
    diff = parse_num(diff_m.group(1)) if diff_m else 0
    # 등락률
    pct_m = re.search(r'id="_rate"[^>]*>([\d.]+)<', html)
    pct = parse_float(pct_m.group(1)) if pct_m else 0.0
    # 상승/하락 판단
    sign_m = re.search(r'class="(up|dn)\b[^"]*"\s*id="_itemUpDown"', html)
    if sign_m and sign_m.group(1) == "dn":
        diff = -diff
        pct  = -pct
    if name and price:
        return {"name": name, "price": price, "diff": diff, "pct": pct}
    return None

def fetch_price(ticker):
    code = ticker.zfill(6)
    methods = [
        ("모바일API", try_mobile_api),
        ("금융API",   try_finance_api),
        ("HTML스크랩", try_sise_html),
    ]
    for method_name, fn in methods:
        try:
            result = fn(code)
            if result:
                return result, method_name
        except Exception:
            pass
        time.sleep(0.1)
    return None, None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "prices.json")

    print(f"총 {len(TICKERS)}개 종목 가격 갱신 시작...")
    print("-" * 50)

    results = {}
    ok, fail = 0, 0

    for i, ticker in enumerate(TICKERS, 1):
        data, method = fetch_price(ticker)
        if data:
            results[ticker] = data
            sign = "+" if data["pct"] >= 0 else ""
            print(f"[{i:3}/{len(TICKERS)}] OK  {ticker}  {data['name'][:18]:<18}  {data['price']:>8,}원  {sign}{data['pct']:.2f}%  ({method})")
            ok += 1
        else:
            print(f"[{i:3}/{len(TICKERS)}] FAIL {ticker}")
            fail += 1
        time.sleep(0.2)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    print(f"\n완료!  성공 {ok}개 / 실패 {fail}개")
    print(f"저장: {output_path}")
    if fail > 0:
        failed = [t for t in TICKERS if t not in results]
        print(f"실패 티커: {failed}")
    print("\n브라우저에서 현황판을 새로고침(F5)하면 업데이트됩니다.")

if __name__ == "__main__":
    main()
