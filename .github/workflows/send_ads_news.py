#!/usr/bin/env python3
"""
每日廣告投放簡報
涵蓋：Meta Ads / Google Ads / GA4 / 數位行銷趨勢
分析：Groq Llama 3.3 70B（繁體中文）
推播：Telegram
"""

import os, re, html, time
from datetime import datetime, timezone, timedelta
import requests, feedparser

# ── 時區 ──────────────────────────────────────────────────────────────────────
tz       = timezone(timedelta(hours=8))
now      = datetime.now(tz)
date_str = now.strftime("%Y/%m/%d")
weekday  = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]

TOKEN    = os.environ["TELEGRAM_TOKEN"]
CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
GROQ_KEY = os.environ["GROQ_API_KEY"]
HEADERS  = {'User-Agent': 'Mozilla/5.0 (compatible; adsbot/1.0)'}

SYSTEM = (
    "你是一位資深數位廣告投放專家，精通 Meta Ads、Google Ads、GA4、程序化廣告。"
    "你的任務是將英文廣告業界新聞翻譯並整理成繁體中文摘要，"
    "重點說明每則新聞對廣告投放實務的影響（如：預算分配、出價策略、受眾設定、報表解讀）。"
    "語言：繁體中文。風格：專業、簡潔、有實務建議。"
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

def clean(text, maxlen=350):
    if not text: return ''
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:maxlen]

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
                        {"role": "system", "content": SYSTEM},
                        {"role": "user",   "content": prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.6
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

# ── RSS 抓取 ──────────────────────────────────────────────────────────────────
def rss(url, n=8):
    try:
        feed = feedparser.parse(url)
        out  = []
        for e in feed.entries[:n]:
            t   = e.get('title', '').strip()
            lnk = e.get('link', '').strip()
            raw = (e.get('summary') or e.get('description') or
                   (e.get('content', [{}])[0].get('value', '') if e.get('content') else ''))
            sm  = clean(raw, 300)
            if t:
                out.append({'title': t, 'url': lnk, 'summary': sm})
        return out
    except Exception as e:
        print(f"rss({url}) error: {e}")
        return []

# ── 廣告業界新聞來源 ──────────────────────────────────────────────────────────
print("抓取廣告業界 RSS...")

# Google Ads 官方
google_ads   = rss("https://ads.googleblog.com/feeds/posts/default", 6)
# Search Engine Land（涵蓋 Google/Meta Ads 深度報導）
sel          = rss("https://searchengineland.com/feed", 8)
# Search Engine Journal
sej          = rss("https://www.searchenginejournal.com/feed/", 6)
# Social Media Examiner（Meta Ads 為主）
sme          = rss("https://www.socialmediaexaminer.com/feed/", 6)
# Marketing Brew
mktbrew      = rss("https://www.marketingbrew.com/feed", 5)
# The Keyword（Google 官方部落格）
google_blog  = rss("https://blog.google/rss/", 5)

# 合併去重
seen = set()
all_news = []
for item in google_ads + sel + sej + sme + mktbrew + google_blog:
    if item['title'] not in seen:
        seen.add(item['title'])
        all_news.append(item)

print(f"共抓到 {len(all_news)} 則新聞")

# ── 分類關鍵字 ────────────────────────────────────────────────────────────────
def pick(pool, kws, n=4):
    found = [x for x in pool if any(k.lower() in x['title'].lower() or
             k.lower() in x['summary'].lower() for k in kws)]
    return found[:n]

def fill_to(lst, pool, min_n):
    used = {x['url'] for x in lst}
    for x in pool:
        if len(lst) >= min_n: break
        if x['url'] not in used and x.get('url'):
            lst.append(x)
            used.add(x['url'])
    return lst

meta_kw    = ['meta','facebook','instagram','reels','advantage','pixel','capi','whatsapp',
              'audience network','lead ads','shop ads']
google_kw  = ['google ads','adwords','pmax','performance max','smart bidding','quality score',
              'search ads','shopping ads','demand gen','youtube ads','google ad']
ga4_kw     = ['ga4','google analytics','analytics 4','measurement','conversion tracking',
              'attribution','gtm','tag manager','data stream']
ai_kw      = ['ai','artificial intelligence','machine learning','automation','smart campaign',
              'broad match','responsive','generative','llm','chatgpt']
general_kw = ['advertis','campaign','bidding','audience','targeting','cpc','cpm','roas','cpa',
              'landing page','creative','a/b test','privacy','cookie','attribution']

meta_news    = pick(all_news, meta_kw, 4)
google_news  = pick(all_news, google_kw, 4)
ga4_news     = pick(all_news, ga4_kw, 3)
ai_ads_news  = pick(all_news, ai_kw, 3)
general_news = pick(all_news, general_kw, 3)

# 補足每區至少 2 條
meta_news    = fill_to(meta_news,    all_news, 2)
google_news  = fill_to(google_news,  all_news, 2)
ga4_news     = fill_to(ga4_news,     all_news, 2)
ai_ads_news  = fill_to(ai_ads_news,  all_news, 2)
general_news = fill_to(general_news, all_news, 2)

# ── 組合給 AI 的新聞脈絡 ──────────────────────────────────────────────────────
def build_context():
    lines = [f"以下是今日（{date_str} {weekday}）廣告業界最新英文新聞：\n"]

    def section(title, items):
        if not items: return
        lines.append(f"【{title}】")
        for i, n in enumerate(items[:4]):
            lines.append(f"{i+1}. {n['title']}")
            if n['summary']: lines.append(f"   {n['summary'][:250]}")
        lines.append("")

    section("Meta Ads / Facebook / Instagram", meta_news)
    section("Google Ads / PMax / Smart Bidding", google_news)
    section("GA4 / 數據分析 / 追蹤", ga4_news)
    section("AI 廣告自動化", ai_ads_news)
    section("數位行銷趨勢", general_news)
    return "\n".join(lines)

# ── MSG1：AI 分析摘要 ─────────────────────────────────────────────────────────
def generate_msg1(ctx):
    prompt = f"""{ctx}

請用繁體中文撰寫今日廣告投放日報，嚴格按照以下格式輸出：

📢 廣告投放日報｜{date_str}（{weekday}）

📘 Meta Ads 動態

① [標題：描述最重要的 Meta Ads 更新，含具體功能名稱]
[2-3句：說明這個更新是什麼、對廣告投放有什麼影響、投放人員應如何因應]

② [標題：第二則重要更新]
[2-3句分析]

🔍 Google Ads 動態

① [標題：描述最重要的 Google Ads 更新，含具體功能或政策名稱]
[2-3句：說明更新內容、對出價/受眾/廣告素材的影響、實務建議]

② [標題：第二則重要更新]
[2-3句分析]

📊 GA4 / 數據追蹤

① [標題：GA4 或追蹤相關更新]
[2-3句：說明影響的功能、數據解讀注意事項]

🤖 AI 廣告自動化趨勢

① [標題：AI 對廣告投放的最新影響]
[2-3句：具體說明哪個平台、哪個功能、投放人員需要注意什麼]

🌐 數位行銷趨勢

① [標題：其他重要行銷趨勢]
[2句摘要]

⚡ 今日重點提醒
• [具體操作建議或注意事項]
• [具體操作建議或注意事項]
• [具體操作建議或注意事項]

【規定】
- 每個標題要具體（含平台名稱、功能名稱），不要用「廣告投放更新」這種廢話標題
- 分析要說明對「實際投放操作」的影響，不只是翻譯新聞
- 全文繁體中文"""

    print("呼叫 Groq API 生成廣告日報 MSG1...")
    return call_llm(prompt)

# ── MSG2：新聞連結整理 ────────────────────────────────────────────────────────
NUMS = "①②③④⑤"

def news_block(header, items, n=4):
    if not items: return ""
    lines = [header]
    count = 0
    for item in items[:n]:
        if not item.get('url'): continue
        lines.append(f"{NUMS[count]} {item['title']}")
        lines.append(f"   {item['url']}")
        count += 1
    return "\n".join(lines) if count > 0 else ""

def generate_msg2():
    parts = [f"📰 廣告業界新聞連結｜{date_str}（{weekday}）\n"]

    for header, items in [
        ("📘 Meta Ads",          meta_news[:4]),
        ("🔍 Google Ads",        google_news[:4]),
        ("📊 GA4 / 數據分析",    ga4_news[:3]),
        ("🤖 AI 廣告自動化",     ai_ads_news[:3]),
        ("🌐 數位行銷",          general_news[:3]),
    ]:
        b = news_block(header, items)
        if b: parts.append(b)

    parts.append("📚 資料來源：Search Engine Land / SEJ / Social Media Examiner / Google Blog")
    return "\n\n".join(parts)

# ── 主流程 ────────────────────────────────────────────────────────────────────
ctx  = build_context()
msg1 = generate_msg1(ctx)
msg2 = generate_msg2()

print("── 第一則：廣告業界分析 ──")
print(msg1[:300], "...")
send_telegram(msg1)

print("── 第二則：新聞連結 ──")
print(msg2[:300], "...")
send_telegram(msg2)

print("✅ 完成")
