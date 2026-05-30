import requests
import feedparser
import os
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_str = now.strftime("%Y/%m/%d")
weekday = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]

def fetch_rss(url, limit=4):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '').strip()
            if title:
                items.append(f"• {title}")
        return items
    except Exception as e:
        return []

# 抓取各財經 RSS 來源
cnyes_tw  = fetch_rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 4)
cnyes_us  = fetch_rss("https://www.cnyes.com/rss/cat/us_stock.xml", 3)
cnyes_mac = fetch_rss("https://www.cnyes.com/rss/cat/economy.xml", 3)

# 備援
if not cnyes_tw:
    cnyes_tw = ["• 請至 cnyes.com 查看今日台股動態"]
if not cnyes_us:
    cnyes_us = ["• 請至 cnyes.com 查看今日美股動態"]
if not cnyes_mac:
    cnyes_mac = ["• 請至 cnyes.com 查看總體經濟資訊"]

tw_text  = "\n".join(cnyes_tw)
us_text  = "\n".join(cnyes_us)
mac_text = "\n".join(cnyes_mac)

message = (
    f"📈 每日財經簡報 {date_str}（{weekday}）\n\n"
    f"🇹🇼 台股重點新聞\n{tw_text}\n\n"
    f"🌏 美股 / 國際市場\n{us_text}\n\n"
    f"📊 總體經濟\n{mac_text}\n\n"

    f"⚡ 今日提醒\n"
    f"• 台股交易時間：09:00-13:30\n"
    f"• 留意三大法人買賣超動向\n"
    f"• 重大消息請至公開資訊觀測站確認\n\n"
    f"📚 資料來源：鉅亨網 RSS"
)

token   = os.environ["TELEGRAM_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

resp = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data={"chat_id": chat_id, "text": message}
)

if resp.json().get("ok"):
    print("推播成功！")
else:
    print(f"推播失敗：{resp.text}")
    exit(1)
