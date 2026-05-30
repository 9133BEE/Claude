import requests
import feedparser
import os
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_str = now.strftime("%Y/%m/%d")
weekday = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]
hour = now.hour  # 9 = 早盤簡報, 18 = 收盤復盤

def fetch_rss(url, limit=4):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '').strip()
            link  = entry.get('link', '').strip()
            if title and link:
                items.append(f"• {title}\n  {link}")
            elif title:
                items.append(f"• {title}")
        return items
    except Exception:
        return []

# RSS 來源
cnyes_tw  = fetch_rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 4)
cnyes_us  = fetch_rss("https://www.cnyes.com/rss/cat/us_stock.xml", 4)
cnyes_mac = fetch_rss("https://www.cnyes.com/rss/cat/economy.xml", 3)

# 備援
if not cnyes_tw:
    cnyes_tw = ["• 請至 cnyes.com 查看台股動態\n  https://www.cnyes.com/twstock/"]
if not cnyes_us:
    cnyes_us = ["• 請至 cnyes.com 查看美股動態\n  https://www.cnyes.com/usstock/"]
if not cnyes_mac:
    cnyes_mac = ["• 請至 cnyes.com 查看總體經濟\n  https://www.cnyes.com/economy/"]

tw_text  = "\n\n".join(cnyes_tw)
us_text  = "\n\n".join(cnyes_us)
mac_text = "\n\n".join(cnyes_mac)

is_weekday = now.weekday() < 5  # 週一~週五

if hour < 14:
    # ── 早盤簡報（09:00）──────────────────────────
    session_label = "早盤簡報"
    tw_header  = "🇹🇼 台股今日重點新聞"
    us_header  = "🌏 美股 / 國際市場"
    mac_header = "📊 總體經濟"
    reminder = (
        "⚡ 開盤前注意事項\n"
        "• 台股交易時間：09:00–13:30\n"
        "• 留意三大法人開盤動向\n"
        "• 重大消息請至公開資訊觀測站確認\n"
        "  https://mops.twse.com.tw"
    )
else:
    # ── 收盤復盤（18:00）──────────────────────────
    session_label = "收盤復盤"
    tw_header  = "🇹🇼 台股今日收盤新聞"
    us_header  = "🌏 美股盤前 / 國際市場"
    mac_header = "📊 總體經濟"
    reminder = (
        "⚡ 盤後注意事項\n"
        "• 留意三大法人今日買賣超\n"
        "• 關注美股期貨與亞股表現\n"
        "• 法說會 / 重大公告請至公開資訊觀測站\n"
        "  https://mops.twse.com.tw"
    )

if not is_weekday:
    tw_section = (
        "🇹🇼 台股今日休市（週末）\n"
        "• 下週一開盤前請留意美股及外資動向\n"
        "  https://www.cnyes.com/twstock/"
    )
else:
    tw_section = f"{tw_header}\n{tw_text}"

message = (
    f"📈 每日財經簡報｜{date_str}（{weekday}）{session_label}\n\n"
    f"{tw_section}\n\n"
    f"{us_header}\n{us_text}\n\n"
    f"{mac_header}\n{mac_text}\n\n"
    f"{reminder}\n\n"
    f"📚 資料來源：鉅亨網 RSS\n"
    f"🔗 更多資訊：https://www.cnyes.com"
)

token   = os.environ["TELEGRAM_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

resp = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data={"chat_id": chat_id, "text": message}
)

if resp.json().get("ok"):
    print(f"推播成功！（{session_label}）")
else:
    print(f"推播失敗：{resp.text}")
    exit(1)
