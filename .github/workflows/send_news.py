#!/usr/bin/env python3
"""
每日財經簡報 — Gemini AI 撰寫版（免費）
資料收集：Yahoo Finance + TWSE + RSS
分析撰寫：Google Gemini 1.5 Flash
推播：Telegram
"""

import os, re, html
from datetime import datetime, timezone, timedelta
import requests, feedparser
import google.generativeai as genai

# ── 時區 ──────────────────────────────────────────────────────────────────────
tz         = timezone(timedelta(hours=8))
now        = datetime.now(tz)
date_str   = now.strftime("%Y/%m/%d")
weekday    = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]
hour       = now.hour
is_morning = hour < 14
session    = "早盤簡報" if is_morning else "收盤復盤"
today_date = now.strftime("%Y%m%d")

TOKEN    = os.environ["TELEGRAM_TOKEN"]
CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
HEADERS  = {'User-Agent': 'Mozilla/5.0 (compatible; finbot/1.0)'}

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=(
        "你是台灣頂尖的金融市場分析師，專精於台股、美股、總體經濟分析。"
        "你的分析風格：每個論點必須引用具體數字（指數點位、漲跌幅、成交量、金額）；"
        "說明「為什麼」而不只是「是什麼」；每個分析段落至少 4 句話，150 字以上；"
        "整篇分析要有連貫的市場邏輯，而不是各點獨立的片段。"
    )
)

def send_telegram(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False},
        timeout=30
    )
    ok = r.json().get("ok")
    print("Telegram:", "OK" if ok else r.text[:200])
    return ok

# ── HTML 清理 ─────────────────────────────────────────────────────────────────
def clean(text, maxlen=400):
    if not text: return ''
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    for prefix in ['（本文出自', '延伸閱讀', '更多相關新聞', '資料來源：', '※', '▲']:
        idx = text.find(prefix)
        if idx > 30:
            text = text[:idx].strip()
    return text[:maxlen]

# ── Yahoo Finance ─────────────────────────────────────────────────────────────
def yf(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo"
        d = requests.get(url, headers=HEADERS, timeout=12).json()
        result = d['chart']['result'][0]
        meta   = result['meta']
        price  = meta.get('regularMarketPrice') or 0
        prev   = meta.get('previousClose') or meta.get('chartPreviousClose') or price
        chg    = round(price - prev, 2)
        pct    = round(chg / prev * 100, 2) if prev else 0
        closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
        valid  = [c for c in closes if c]
        m_open = valid[0] if valid else price
        m_chg  = round(price - m_open, 2)
        m_pct  = round(m_chg / m_open * 100, 2) if m_open else 0
        return {'p': price, 'chg': chg, 'pct': pct, 'mchg': m_chg, 'mpct': m_pct}
    except Exception as e:
        print(f"yf({symbol}) error: {e}")
        return None

def fmt(d):
    if not d: return 'N/A'
    sign = '+' if d['chg'] >= 0 else ''
    return f"{d['p']:,.2f}（{sign}{d['pct']:.2f}%，本月{sign}{d['mpct']:.2f}%）"

# ── 台交所三大法人 ────────────────────────────────────────────────────────────
def get_inst():
    try:
        url = (f"https://www.twse.com.tw/rwd/zh/fund/T86"
               f"?response=json&date={today_date}&selectType=ALLBUT0999")
        d = requests.get(url, headers=HEADERS, timeout=12).json()
        if d.get('stat') != 'OK' or not d.get('data'):
            return None
        r = {}
        for row in d['data']:
            name = str(row[0])
            def p(x): return int(str(x).replace(',','').replace(' ','') or 0)
            net = p(row[3]) if len(row) > 3 else 0
            if '外資' in name and '陸資' not in name: r['foreign'] = net
            elif '投信' in name:   r['trust']   = net
            elif '自營商' in name: r['dealer']  = net
        return r if r else None
    except Exception as e:
        print(f"inst error: {e}")
        return None

def amt(n):
    if n is None: return 'N/A'
    return f"{'+'if n>0 else ''}{n/1e8:.1f}億"

# ── RSS 抓取 ──────────────────────────────────────────────────────────────────
def rss(url, n=12):
    try:
        feed = feedparser.parse(url)
        out  = []
        for e in feed.entries[:n]:
            t   = e.get('title', '').strip()
            lnk = e.get('link', '').strip()
            raw = (e.get('summary') or e.get('description') or
                   (e.get('content', [{}])[0].get('value', '') if e.get('content') else ''))
            sm  = clean(raw, 350)
            if t:
                out.append({'title': t, 'url': lnk, 'summary': sm})
        return out
    except Exception as e:
        print(f"rss({url}) error: {e}")
        return []

# ── 收集所有數據 ──────────────────────────────────────────────────────────────
print("收集市場數據...")
taiex  = yf("%5ETWII")
tsmc   = yf("2330.TW")
hon    = yf("2317.TW")
nvidia = yf("NVDA")
dji    = yf("%5EDJI")
spx    = yf("%5EGSPC")
ixic   = yf("%5EIXIC")
dxy    = yf("DX-Y.NYB")
t10y   = yf("%5ETNX")
inst   = get_inst()

print("抓取新聞 RSS...")
tw1  = rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 12)
tw2  = rss("https://money.udn.com/rssfeed/news/1/5607?ch=money", 8)
us1  = rss("https://www.cnyes.com/rss/cat/us_stock.xml", 10)
mac1 = rss("https://www.cnyes.com/rss/cat/economy.xml", 8)

seen = set()
tw_all = []
for n in tw1 + tw2:
    if n['title'] not in seen:
        seen.add(n['title'])
        tw_all.append(n)

# ── 組合給 Gemini 的原始資料 ──────────────────────────────────────────────────
def build_data_context():
    lines = []
    lines.append(f"=== 即時市場數據（{date_str} {weekday} {session}）===")
    lines.append("")
    lines.append("【台股指數】")
    if taiex:
        lines.append(f"加權指數：{fmt(taiex)}")
    if inst:
        f = inst.get('foreign'); t = inst.get('trust'); d = inst.get('dealer')
        total = (f or 0) + (t or 0) + (d or 0)
        lines.append(f"外資：{amt(f)}  投信：{amt(t)}  自營商：{amt(d)}  合計：{amt(total)}")
    lines.append("")
    lines.append("【台股重點個股】")
    if tsmc: lines.append(f"台積電(2330)：{fmt(tsmc)}")
    if hon:  lines.append(f"鴻海(2317)：{fmt(hon)}")
    lines.append("")
    lines.append("【美股指數】")
    if dji:    lines.append(f"道瓊：{fmt(dji)}")
    if spx:    lines.append(f"標普500：{fmt(spx)}")
    if ixic:   lines.append(f"那斯達克：{fmt(ixic)}")
    if nvidia: lines.append(f"NVIDIA(NVDA)：{fmt(nvidia)}")
    lines.append("")
    lines.append("【總體經濟】")
    if dxy:  lines.append(f"美元指數(DXY)：{fmt(dxy)}")
    if t10y: lines.append(f"美國10年期公債殖利率：{t10y['p']:.3f}%（{'+' if t10y['chg']>=0 else ''}{t10y['chg']:.3f}%）")
    lines.append("")
    lines.append("=== 最新新聞 ===")
    lines.append("")
    lines.append("【台股新聞】")
    for i, n in enumerate(tw_all[:10]):
        lines.append(f"{i+1}. {n['title']}")
        if n['summary']: lines.append(f"   摘要：{n['summary']}")
        if n['url']:     lines.append(f"   連結：{n['url']}")
    lines.append("")
    lines.append("【美股新聞】")
    for i, n in enumerate(us1[:8]):
        lines.append(f"{i+1}. {n['title']}")
        if n['summary']: lines.append(f"   摘要：{n['summary']}")
        if n['url']:     lines.append(f"   連結：{n['url']}")
    lines.append("")
    lines.append("【總體經濟新聞】")
    for i, n in enumerate(mac1[:6]):
        lines.append(f"{i+1}. {n['title']}")
        if n['summary']: lines.append(f"   摘要：{n['summary']}")
        if n['url']:     lines.append(f"   連結：{n['url']}")
    return "\n".join(lines)

# ── 生成 MSG1（市場深度分析）────────────────────────────────────────────────
def generate_msg1(data_ctx):
    prompt = f"""以下是今日（{date_str} {weekday}）最新市場數據與新聞：

{data_ctx}

請根據以上數據與新聞，撰寫「市場資金動向詳細分析」。

【重要】參考以下範例的寫作深度與風格（這是你應達到的標準）：

範例格式（每個分析點至少這樣的深度）：
① 本月指數強漲 4,700 點，挑戰史上最強 5 月
加權指數今日收 44,256 點（+1.23%），成交量爆出 4,521 億天量，外資單日買超 803 億創今年第二高。月初台股 39,556 點，至今累漲 4,700 點（+11.88%），已超越 2021 年 7 月單月漲幅 4,200 點，挑戰史上最強五月紀錄。資金面由 AI 伺服器訂單爆發驅動，輝達 GB200 供應鏈全面拉貨，法人預估 Q3 訂單能見度高達 18 個月。技術面站上所有均線，月線乖離率達 12%，短線雖有過熱疑慮，但籌碼集中度持續提升。

② 外資連 8 日買超，累計鎖碼逾 2,200 億
外資今日買超 803 億，連續第 8 個交易日買超，累計金額突破 2,200 億元，為今年最長連買紀錄。投信加碼 42 億，自營商買超 38 億，三大法人合計買超 883 億，籌碼集中效應明顯。外資鎖定台積電（買超逾 350 億）與鴻海（買超逾 120 億），顯示資金主要追蹤 AI 算力供應鏈核心標的。法人籌碼持續擴增，意味市場對 Q3 台股業績能見度信心充足。

現在用上方提供的【真實數據】，依照此深度與風格撰寫今日分析：

📈 每日財經簡報｜{date_str}（{weekday}）{session}

🇹🇼 台股市場

① [標題：反映最重要台股動態，要有具體數字]
[4-5句分析：引用指數點位、漲跌幅、成交量；說明月度背景；分析資金驅動邏輯；技術面解讀]

② [標題：三大法人籌碼分析，包含具體金額]
[4-5句分析：外資/投信/自營商各別金額；分析法人偏好標的與操作邏輯；說明籌碼面對後市意義]

③ [標題：台積電/鴻海等權值股動態]
[4-5句分析：具體股價漲跌幅；外資目標價或法說重點；產業趨勢；供應鏈連動效應]

④ [標題：今日最重要財報或題材]
[4句分析：具體數字+深度解讀+受惠族群]

🌏 美股市場

① [標題：美股三大指數昨夜動態]
[4句分析：具體指數點位漲跌；推動因素；對今日台股的傳導效應]

② [標題：NVIDIA/AI科技股動態]
[4句分析：具體股價；財報或題材驅動；台灣供應鏈受惠情況]

③ [標題：其他重點美股事件]
[3句分析：具體數字+市場影響]

📊 總體經濟

① [標題：Fed/利率/通膨最新動態]
[4句分析：具體數字；政策方向；對股市債市影響]

② [標題：美債殖利率/美元指數]
[3句分析：具體數字+對科技股估值或新興市場的影響]

⚡ 今日注意事項
• [具體財經事件，不要寫廢話]
• [具體財經事件]
• [具體財經事件]

【強制規則】
- 每個分析點必須引用具體數字（從上方數據中取用）
- 每個分析段落至少 4 句話
- 禁止使用「持續走高」「表現良好」「值得關注」等空泛詞彙
- 整篇總長度 2000-2500 字元"""

    print("呼叫 Gemini API 生成 MSG1...")
    response = model.generate_content(prompt)
    return response.text

# ── 生成 MSG2（重點新聞連結）────────────────────────────────────────────────
def generate_msg2(data_ctx):
    prompt = f"""以下是今日（{date_str} {weekday}）最新新聞（含連結）：

{data_ctx}

請整理「重點新聞連結」，格式如下：

📰 重點新聞連結｜{date_str}（{weekday}）

🇹🇼 資金流向
① [新聞標題]
   [完整文章URL]
② [新聞標題]
   [完整文章URL]
③ [新聞標題]
   [完整文章URL]

📋 重點財報
① [新聞標題]
   [完整文章URL]
② [新聞標題]
   [完整文章URL]

🎯 預期受惠股
① [新聞標題]
   [完整文章URL]
② [新聞標題]
   [完整文章URL]

🌏 美股動態
① [新聞標題]
   [完整文章URL]
② [新聞標題]
   [完整文章URL]
③ [新聞標題]
   [完整文章URL]

📊 總體經濟
① [新聞標題]
   [完整文章URL]
② [新聞標題]
   [完整文章URL]

規則：
- 只使用上方原始資料中提供的真實 URL，不可捏造連結
- 如某分類無相關新聞可少幾條，但不放假連結
- 總長度控制在 1200 字元以內"""

    print("呼叫 Gemini API 生成 MSG2...")
    response = model.generate_content(prompt)
    return response.text

# ── 主流程 ────────────────────────────────────────────────────────────────────
data_context = build_data_context()

msg1 = generate_msg1(data_context)
msg2 = generate_msg2(data_context)

print("── 第一則：市場分析 ──")
print(msg1[:300], "...")
send_telegram(msg1)

print("── 第二則：新聞連結 ──")
print(msg2[:300], "...")
send_telegram(msg2)

print("✅ 完成")
