#!/usr/bin/env python3
"""
每日財經簡報 — 2 則推送
  1. sendMessage — 台股/美股/總體詳細文字摘要（資金流向、重點財報、預期受惠股）
  2. sendMessage — 重點新聞連結（同三類）
"""

import os
from datetime import datetime, timezone, timedelta
import requests, feedparser

# ── 時間 ──────────────────────────────────────────────────────────────────────
tz         = timezone(timedelta(hours=8))
now        = datetime.now(tz)
date_str   = now.strftime("%Y/%m/%d")
weekday    = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]
hour       = now.hour
is_morning = hour < 14
is_weekday = now.weekday() < 5
session    = "早盤簡報" if is_morning else "收盤復盤"

# ── RSS 抓取 ──────────────────────────────────────────────────────────────────
def fetch_rss(url, limit=8):
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:limit]:
            t = e.get('title', '').strip()
            l = e.get('link',  '').strip()
            if t:
                items.append({'title': t, 'link': l})
        return items
    except Exception:
        return []

tw_pool  = fetch_rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 10)
us_pool  = fetch_rss("https://www.cnyes.com/rss/cat/us_stock.xml", 10)
mac_pool = fetch_rss("https://www.cnyes.com/rss/cat/economy.xml",   8)

# ── 關鍵字分類 ────────────────────────────────────────────────────────────────
CAPITAL_KW    = ['外資','法人','買超','賣超','資金','籌碼','三大法人','投信','自營',
                 'ETF','MSCI','融資','融券','主力','ADR','GDR']
EARNINGS_KW   = ['財報','業績','EPS','獲利','營收','淨利','虧損','法說','展望',
                 '毛利','季報','年報','盈利','稅後']
BENEFICIARY_KW= ['受惠','利多','目標價','上調','調升','看好','漲停','創高','突破',
                 'AI','人工智慧','半導體','輝達','黃仁勳','供應鏈','訂單','題材']

def categorize(pool):
    capital, earnings, beneficiary, other = [], [], [], []
    for item in pool:
        t = item['title']
        if any(k in t for k in CAPITAL_KW):
            capital.append(item)
        elif any(k in t for k in EARNINGS_KW):
            earnings.append(item)
        elif any(k in t for k in BENEFICIARY_KW):
            beneficiary.append(item)
        else:
            other.append(item)
    # 若某類別空白，從 other 補一條
    if not capital    and other: capital.append(other.pop(0))
    if not earnings   and other: earnings.append(other.pop(0))
    if not beneficiary and other: beneficiary.append(other.pop(0))
    return capital[:3], earnings[:3], beneficiary[:3]

tw_cap,  tw_ear,  tw_ben  = categorize(tw_pool)
us_cap,  us_ear,  us_ben  = categorize(us_pool)
mac_cap, mac_ear, mac_ben = categorize(mac_pool)

# ── Telegram 推送 ─────────────────────────────────────────────────────────────
TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_msg(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )
    ok = r.json().get("ok")
    print("sendMessage:", "OK" if ok else r.text[:120])
    return ok

def titles(lst):
    return "\n".join(f"  • {n['title']}" for n in lst) if lst else "  • 暫無相關資訊"

def links(lst):
    if not lst:
        return "  • 暫無相關資訊"
    lines = []
    for i, n in enumerate(lst, 1):
        lines.append(f"  {i}. {n['title']}")
        if n.get('link'):
            lines.append(f"     {n['link']}")
    return "\n".join(lines)

# ════════════════════════════════════════════════════════════════════════════
# 第一則：詳細文字摘要
# ════════════════════════════════════════════════════════════════════════════
tw_closed = not is_weekday

msg1 = f"""📈 每日財經簡報｜{date_str}（{weekday}）{session}

{'='*30}
🇹🇼 台股
{'='*30}
"""
if tw_closed:
    msg1 += "今日休市（週末）\n\n"
else:
    msg1 += f"""💰 資金流向
{titles(tw_cap)}

📋 重點財報 / 業績
{titles(tw_ear)}

🎯 預期受惠股 / 題材
{titles(tw_ben)}

"""

msg1 += f"""{'='*30}
🌏 美股 / 國際市場
{'='*30}
💰 資金流向
{titles(us_cap)}

📋 重點財報 / 業績
{titles(us_ear)}

🎯 預期受惠股 / 題材
{titles(us_ben)}

{'='*30}
📊 總體經濟
{'='*30}
💰 資金 / 央行動向
{titles(mac_cap)}

📋 重要數據 / 財報
{titles(mac_ear)}

🎯 市場展望 / 受惠方向
{titles(mac_ben)}

⚡ {'開盤前' if is_morning else '盤後'}注意
  • 台股交易時間：09:00–13:30
  • 留意三大法人買賣超方向
  • 重大公告 → mops.twse.com.tw

📚 資料來源：鉅亨網 RSS"""

# ════════════════════════════════════════════════════════════════════════════
# 第二則：重點新聞連結
# ════════════════════════════════════════════════════════════════════════════
msg2 = f"""🔗 重點新聞連結｜{date_str}（{weekday}）

{'='*30}
🇹🇼 台股
{'='*30}
"""
if tw_closed:
    msg2 += "今日休市（週末）\n\n"
else:
    msg2 += f"""💰 資金流向
{links(tw_cap)}

📋 重點財報 / 業績
{links(tw_ear)}

🎯 預期受惠股 / 題材
{links(tw_ben)}

"""

msg2 += f"""{'='*30}
🌏 美股 / 國際市場
{'='*30}
💰 資金流向
{links(us_cap)}

📋 重點財報 / 業績
{links(us_ear)}

🎯 預期受惠股 / 題材
{links(us_ben)}

{'='*30}
📊 總體經濟
{'='*30}
💰 資金 / 央行動向
{links(mac_cap)}

📋 重要數據 / 財報
{links(mac_ear)}

🎯 市場展望 / 受惠方向
{links(mac_ben)}

📚 資料來源：鉅亨網 RSS"""

# ════════════════════════════════════════════════════════════════════════════
print("── 第一則：文字摘要 ──")
send_msg(msg1)

print("── 第二則：新聞連結 ──")
send_msg(msg2)
