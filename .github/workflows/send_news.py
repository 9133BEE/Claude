#!/usr/bin/env python3
"""
每日財經簡報 — Gemini AI 撰寫版（免費）
資料收集：Yahoo Finance + TWSE + RSS
分析撰寫：Google Gemini 1.5 Flash
推播：Telegram
"""

import os, re, html, time
from datetime import datetime, timezone, timedelta
import requests, feedparser

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
GROQ_KEY = os.environ["GROQ_API_KEY"]
HEADERS  = {'User-Agent': 'Mozilla/5.0 (compatible; finbot/1.0)'}

LLM_SYSTEM = (
    "你是台灣頂尖的金融市場分析師，專精於台股、美股、總體經濟分析。"
    "你的分析風格：每個論點必須引用具體數字（指數點位、漲跌幅、成交量、金額）；"
    "說明「為什麼」而不只是「是什麼」；每個分析段落至少 4 句話；"
    "整篇分析要有連貫的市場邏輯，而不是各點獨立的片段。"
)

def call_llm(prompt, retries=3):
    for attempt in range(retries):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": LLM_SYSTEM},
                        {"role": "user",   "content": prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.7
                },
                timeout=60
            )
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"Rate limit，等待 {wait} 秒後重試...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content']
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"呼叫失敗（{e}），重試中...")
            time.sleep(10)
    raise Exception("LLM API 重試次數已達上限")

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
tw1  = rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 8)
tw2  = rss("https://money.udn.com/rssfeed/news/1/5607?ch=money", 5)
us1  = rss("https://www.cnyes.com/rss/cat/us_stock.xml", 6)
mac1 = rss("https://www.cnyes.com/rss/cat/economy.xml", 5)

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
    for i, n in enumerate(tw_all[:7]):
        lines.append(f"{i+1}. {n['title']}")
        if n['summary']: lines.append(f"   摘要：{n['summary']}")
        if n['url']:     lines.append(f"   連結：{n['url']}")
    lines.append("")
    lines.append("【美股新聞】")
    for i, n in enumerate(us1[:5]):
        lines.append(f"{i+1}. {n['title']}")
        if n['summary']: lines.append(f"   摘要：{n['summary']}")
        if n['url']:     lines.append(f"   連結：{n['url']}")
    lines.append("")
    lines.append("【總體經濟新聞】")
    for i, n in enumerate(mac1[:4]):
        lines.append(f"{i+1}. {n['title']}")
        if n['summary']: lines.append(f"   摘要：{n['summary']}")
        if n['url']:     lines.append(f"   連結：{n['url']}")
    return "\n".join(lines)

# ── 生成 MSG1（市場深度分析）────────────────────────────────────────────────
def generate_msg1(data_ctx):
    prompt = f"""今日（{date_str} {weekday}）市場數據：

{data_ctx}

用上方真實數據撰寫財經簡報，每個分析點必須含具體數字，每段至少4句，禁止空泛詞彙：

📈 每日財經簡報｜{date_str}（{weekday}）{session}

🇹🇼 台股市場
① [標題含具體指數點位]
[4句：指數漲跌幅+成交量+月度漲幅+資金驅動邏輯]
② [標題含法人買賣超金額]
[4句：外資/投信/自營商各別金額+操作邏輯+後市影響]
③ [標題含台積電/鴻海股價]
[4句：具體股價漲跌+產業趨勢+供應鏈連動]
④ [標題：重點財報或題材]
[3句：具體數字+受惠族群]

🌏 美股市場
① [標題含道瓊/標普/那指點位]
[4句：具體指數+推動因素+對台股傳導]
② [標題含NVIDIA股價]
[3句：股價+AI需求+台廠受惠]
③ [標題：其他重點]
[2句：具體數字+影響]

📊 總體經濟
① [標題：Fed/CPI/PCE具體數字]
[3句：數字+政策方向+市場影響]
② [標題：美債殖利率/美元]
[2句：具體數字+科技股影響]

⚡ 今日注意事項
• [具體事件]
• [具體事件]
• [具體事件]"""

    print("呼叫 Gemini API 生成 MSG1...")
    return call_llm(prompt)

# ── 生成 MSG2（直接格式化，確保連結真實）────────────────────────────────────
NUMS = "①②③④⑤"

def news_block(title, items, n=4):
    lines = [title]
    count = 0
    for item in items:
        if count >= n: break
        if not item.get('url'): continue
        lines.append(f"{NUMS[count]} {item['title']}")
        lines.append(f"   {item['url']}")
        count += 1
    return "\n".join(lines) if count > 0 else ""

def generate_msg2():
    # 關鍵字分類篩選
    capital_kw  = ['外資','法人','買超','賣超','籌碼','三大法人','資金','成交','天量']
    earnings_kw = ['財報','業績','EPS','獲利','營收','法說','配息','股利']
    benefit_kw  = ['受惠','AI','伺服器','供應鏈','台積電','鴻海','半導體','漲停','目標價']
    us_kw       = ['美股','道瓊','標普','那斯達克','NVIDIA','輝達','Fed','聯準','科技']
    macro_kw    = ['GDP','PMI','CPI','PCE','通膨','殖利率','美元','油價','黃金','降息','升息']

    def pick(pool, kws, n=3):
        found = [x for x in pool if any(k in x['title'] for k in kws) and x.get('url')]
        return found[:n]

    all_news = tw_all + us1 + mac1

    capital  = pick(tw_all, capital_kw, 3)
    earnings = pick(all_news, earnings_kw, 3)
    benefit  = pick(tw_all, benefit_kw, 3)
    us_news  = pick(us1, us_kw, 4)
    macro    = pick(mac1, macro_kw, 3)

    # 不夠的用剩餘新聞補
    used = set(x['url'] for x in capital+earnings+benefit+us_news+macro)
    spare_tw = [x for x in tw_all if x.get('url') and x['url'] not in used]
    spare_us = [x for x in us1 if x.get('url') and x['url'] not in used]
    spare_mac = [x for x in mac1 if x.get('url') and x['url'] not in used]

    while len(capital)  < 2 and spare_tw:  capital.append(spare_tw.pop(0))
    while len(earnings) < 2 and spare_tw:  earnings.append(spare_tw.pop(0))
    while len(benefit)  < 2 and spare_tw:  benefit.append(spare_tw.pop(0))
    while len(us_news)  < 3 and spare_us:  us_news.append(spare_us.pop(0))
    while len(macro)    < 2 and spare_mac: macro.append(spare_mac.pop(0))

    parts = [f"📰 重點新聞連結｜{date_str}（{weekday}）\n"]

    b = news_block("🇹🇼 資金流向", capital)
    if b: parts.append(b)
    b = news_block("📋 重點財報", earnings)
    if b: parts.append(b)
    b = news_block("🎯 受惠個股", benefit)
    if b: parts.append(b)
    b = news_block("🌏 美股動態", us_news)
    if b: parts.append(b)
    b = news_block("📊 總體經濟", macro)
    if b: parts.append(b)

    return "\n\n".join(parts)

# ── 主流程 ────────────────────────────────────────────────────────────────────
data_context = build_data_context()

msg1 = generate_msg1(data_context)
msg2 = generate_msg2()   # 直接格式化，不需 AI

print("── 第一則：市場分析 ──")
print(msg1[:300], "...")
send_telegram(msg1)

print("── 第二則：新聞連結 ──")
print(msg2[:300], "...")
send_telegram(msg2)

print("✅ 完成")
