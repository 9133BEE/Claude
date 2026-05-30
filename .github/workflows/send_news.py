#!/usr/bin/env python3
"""
每日財經簡報 — Claude AI 撰寫分析
1. 抓取即時市場數據 + RSS 新聞
2. 呼叫 Claude API 產生專業分析
3. 推播兩則 Telegram
"""

import os, json
from datetime import datetime, timezone, timedelta
import requests, feedparser
import anthropic

# ── 時區 ──────────────────────────────────────────────────────────────────────
tz         = timezone(timedelta(hours=8))
now        = datetime.now(tz)
date_str   = now.strftime("%Y/%m/%d")
weekday    = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]
hour       = now.hour
is_morning = hour < 14
is_weekday = now.weekday() < 5
session    = "早盤簡報" if is_morning else "收盤復盤"
today_date = now.strftime("%Y%m%d")

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_KEY    = os.environ["ANTHROPIC_API_KEY"]

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=30
    )
    ok = r.json().get("ok")
    print("send:", "OK" if ok else r.text[:120])

# ── Yahoo Finance 即時報價 ────────────────────────────────────────────────────
def yf(symbol):
    try:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
               f"?interval=1d&range=5d")
        d = requests.get(url, headers=HEADERS, timeout=12).json()
        meta = d['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice') or 0
        prev  = meta.get('previousClose') or meta.get('chartPreviousClose') or price
        chg   = price - prev
        pct   = chg / prev * 100 if prev else 0
        return {'price': price, 'chg': chg, 'pct': pct}
    except Exception:
        return None

def fmt(d, unit=''):
    if not d: return 'N/A'
    sign = '+' if d['chg'] >= 0 else ''
    return f"{d['price']:,.2f}{unit}（{sign}{d['pct']:.2f}%）"

# ── 台交所三大法人 ────────────────────────────────────────────────────────────
def get_institutional():
    try:
        url = (f"https://www.twse.com.tw/rwd/zh/fund/T86"
               f"?response=json&date={today_date}&selectType=ALLBUT0999")
        d = requests.get(url, headers=HEADERS, timeout=12).json()
        if d.get('stat') != 'OK' or not d.get('data'):
            return None
        result = {}
        for row in d['data']:
            name = str(row[0])
            def p(s): return int(str(s).replace(',','').replace(' ','') or 0)
            net = p(row[3]) if len(row) > 3 else 0
            if '外資' in name and '陸資' not in name: result['foreign'] = net
            elif '投信' in name:   result['trust']   = net
            elif '自營商' in name: result['dealer']  = net
        return result if result else None
    except Exception:
        return None

def fmt_amt(n):
    if n is None: return '無資料'
    sign = '+' if n > 0 else ''
    return f"{sign}{n/1e8:.0f}億"

# ── RSS 新聞 ───────────────────────────────────────────────────────────────────
def rss(url, n=6):
    try:
        feed = feedparser.parse(url)
        out  = []
        for e in feed.entries[:n]:
            t = e.get('title','').strip()
            l = e.get('link','').strip()
            if t: out.append({'title': t, 'link': l})
        return out
    except Exception:
        return []

tw_rss  = rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 6)
us_rss  = rss("https://www.cnyes.com/rss/cat/us_stock.xml", 6)
mac_rss = rss("https://www.cnyes.com/rss/cat/economy.xml",  5)
udn_rss = rss("https://money.udn.com/rssfeed/news/1/5607?ch=money", 5)

def news_fmt(items):
    return '\n'.join(f"  • {n['title']}  {n['link']}" for n in items) or '  • 暫無資料'

# ── 抓市場數據 ────────────────────────────────────────────────────────────────
taiex = yf("%5ETWII")
tsmc  = yf("2330.TW")
hon   = yf("2317.TW")
dji   = yf("%5EDJI")
spx   = yf("%5EGSPC")
ixic  = yf("%5EIXIC")
dxy   = yf("DX-Y.NYB")
t10y  = yf("%5ETNX")
t30y  = yf("%5ETYX")
inst  = get_institutional()

# ── 組合原始資料給 Claude ─────────────────────────────────────────────────────
market_data = f"""
【即時市場數據｜{date_str}（{weekday}）{session}】

台灣市場（台股）：
- 加權指數(^TWII)：{fmt(taiex, ' 點')}
- 台積電(2330.TW)：{fmt(tsmc, ' 元')}
- 鴻海(2317.TW)：{fmt(hon, ' 元')}
- 三大法人今日買賣超：{"外資 "+fmt_amt(inst.get('foreign'))+" / 投信 "+fmt_amt(inst.get('trust'))+" / 自營商 "+fmt_amt(inst.get('dealer')) if inst else "資料更新中（盤中）"}

美國市場（美股）：
- 道瓊工業(^DJI)：{fmt(dji)}
- 標普500(^GSPC)：{fmt(spx)}
- 那斯達克(^IXIC)：{fmt(ixic)}

總體經濟指標：
- 美元指數(DXY)：{fmt(dxy)}
- 10年期美債殖利率：{f"{t10y['price']:.3f}%（{'▲' if t10y['chg']>=0 else '▼'}{abs(t10y['chg']):.3f}%）" if t10y else 'N/A'}
- 30年期美債殖利率：{f"{t30y['price']:.3f}%（{'▲' if t30y['chg']>=0 else '▼'}{abs(t30y['chg']):.3f}%）" if t30y else 'N/A'}
{"- 10Y/30Y 利差："+f"{(t30y['price']-t10y['price']):.3f}%" if t10y and t30y else ""}

【台股今日重點新聞】
{news_fmt(tw_rss + udn_rss)}

【美股今日重點新聞】
{news_fmt(us_rss)}

【總體經濟重點新聞】
{news_fmt(mac_rss)}
"""

# ── Claude AI 撰寫分析 ────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

system_prompt = """你是一位專業的台灣財經市場分析師，負責每日撰寫 Telegram 財經推播。
風格要求：
- 繁體中文，語氣專業但易讀
- 數據引用精確，有具體數字
- 每個重點都要有「標題」+「2-3句說明」
- 重點聚焦：資金流向、法人動態、財報業績、受惠個股/產業
- 不要過度樂觀或悲觀，客觀陳述事實並點出關鍵觀察"""

user_prompt = f"""根據以下今日即時數據與新聞，撰寫兩則 Telegram 推播訊息。

{market_data}

請輸出以下格式（嚴格遵守，不要加任何額外說明）：

===MSG1===
📈 市場資金動向週報｜{date_str}（{weekday}）

🇹🇼 台股市場

① [標題]
[2-3句分析說明，引用具體數據]

② [標題]
[2-3句分析說明，引用具體數據]

③ [標題]
[2-3句分析說明，引用具體數據]

{"④ [標題]" + chr(10) + "[2-3句分析說明]" + chr(10) if is_weekday else ""}
🌏 美股市場

① [標題]
[2-3句分析說明]

② [標題]
[2-3句分析說明]

③ [標題]
[2-3句分析說明]

📊 總體經濟 / 全球資金

① [標題]
[2-3句分析說明]

② [標題]
[2-3句分析說明]

③ [標題]
[2-3句分析說明]

⚡ 今日注意事項
• [注意事項1]
• [注意事項2]
• [注意事項3]
• [注意事項4]

📚 資料來源：Yahoo Finance / 台灣證券交易所 / 鉅亨網
===END1===

===MSG2===
📈 每日財經簡報｜{date_str}（{weekday}）{session}

🇹🇼 台股重點新聞

① [新聞標題]
[對應連結]

② [新聞標題]
[對應連結]

③ [新聞標題]
[對應連結]

④ [新聞標題]
[對應連結]

⑤ [新聞標題]
[對應連結]

🌏 美股重點新聞

① [新聞標題]
[對應連結]

② [新聞標題]
[對應連結]

③ [新聞標題]
[對應連結]

④ [新聞標題]
[對應連結]

📊 總體經濟

① [新聞標題]
[對應連結]

② [新聞標題]
[對應連結]

⚡ 盤後注意事項
• 留意三大法人今日買賣超
• 下週重點：美國就業報告、重量級財報
• 公告查詢：https://mops.twse.com.tw

📚 資料來源：鉅亨網 / 聯合新聞網 / 臺灣證券交易所
===END2===
"""

print("── 呼叫 Claude API ──")
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=4096,
    messages=[{"role": "user", "content": user_prompt}],
    system=system_prompt
)

raw = response.content[0].text

# ── 解析兩則訊息 ──────────────────────────────────────────────────────────────
def extract(raw, tag):
    start = raw.find(f"==={tag}===")
    end   = raw.find(f"===END{tag[-1]}===")
    if start == -1 or end == -1:
        return raw  # fallback: send everything
    return raw[start + len(f"==={tag}==="):end].strip()

msg1 = extract(raw, "MSG1")
msg2 = extract(raw, "MSG2")

print("── 第一則：市場分析 ──")
send(msg1)

print("── 第二則：新聞連結 ──")
send(msg2)

print("✅ 完成")
