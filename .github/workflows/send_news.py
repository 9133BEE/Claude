#!/usr/bin/env python3
"""
每日財經簡報 — 生成 A4 圖片並推送 Telegram
"""

import os
import io
import textwrap
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
import requests
import feedparser

# ── 時間 ──────────────────────────────────────────────────────────────────────
tz       = timezone(timedelta(hours=8))
now      = datetime.now(tz)
date_str = now.strftime("%Y/%m/%d")
weekday  = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]
hour     = now.hour
is_morning  = hour < 14
is_weekday  = now.weekday() < 5
session     = "早盤簡報" if is_morning else "收盤復盤"

# ── RSS ───────────────────────────────────────────────────────────────────────
def fetch_rss(url, limit=4):
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

tw_news  = fetch_rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 4)
us_news  = fetch_rss("https://www.cnyes.com/rss/cat/us_stock.xml", 4)
mac_news = fetch_rss("https://www.cnyes.com/rss/cat/economy.xml",  3)

if not tw_news:
    tw_news  = [{'title':'請至鉅亨網查看台股動態', 'link':'https://www.cnyes.com/twstock/'}]
if not us_news:
    us_news  = [{'title':'請至鉅亨網查看美股動態', 'link':'https://www.cnyes.com/usstock/'}]
if not mac_news:
    mac_news = [{'title':'請至鉅亨網查看總體經濟', 'link':'https://www.cnyes.com/economy/'}]

# ── 字型 ──────────────────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf',
    '/usr/share/fonts/noto-cjk/NotoSansCJKtc-Regular.otf',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    'C:/Windows/Fonts/msjh.ttc',
    'C:/Windows/Fonts/mingliu.ttc',
]

def load_font(size):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

# ── 文字換行（支援中文）────────────────────────────────────────────────────────
def wrap_text(text, font, max_px):
    lines, cur = [], ''
    for ch in text:
        test = cur + ch
        if font.getlength(test) <= max_px:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines

# ── 色票 ──────────────────────────────────────────────────────────────────────
C_BG      = (248, 249, 252)
C_HDR     = (15,  23,  42)
C_WHITE   = (255, 255, 255)
C_TW      = (220, 38,  38)
C_US      = (37,  99,  235)
C_MAC     = (5,   150, 105)
C_TXT     = (15,  23,  42)
C_LINK    = (59,  130, 246)
C_SUB     = (100, 116, 139)
C_DIV     = (226, 232, 240)
C_BADGE   = C_WHITE

# ── 版面 ──────────────────────────────────────────────────────────────────────
W      = 1240
MARGIN = 64
CW     = W - MARGIN * 2   # 可用寬度

# ── 計算總高度（dry-run）────────────────────────────────────────────────────
def measure_height(news_sections):
    f_news = load_font(24)
    f_link = load_font(18)
    y = 140  # header
    for color, title, news_list, is_closed in news_sections:
        y += 56   # section header
        if is_closed:
            y += 44
        else:
            for item in news_list:
                lines = wrap_text(item['title'], f_news, CW - 48)
                y += max(1, len(lines)) * 32 + 4
                if item.get('link'):
                    y += 26
                y += 20  # gap
        y += 24   # section bottom gap
    y += 160   # tips
    y += 70    # footer
    return y + 40

# ── 繪製 ─────────────────────────────────────────────────────────────────────
def generate_image(news_sections):
    H = measure_height(news_sections)
    img  = Image.new('RGB', (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    f_h1   = load_font(40)
    f_date = load_font(22)
    f_sec  = load_font(28)
    f_news = load_font(24)
    f_link = load_font(18)
    f_tip  = load_font(20)
    f_foot = load_font(18)
    f_num  = load_font(17)

    # Header
    draw.rectangle([(0, 0), (W, 128)], fill=C_HDR)
    draw.text((MARGIN, 22),  "📈 每日財經簡報", font=f_h1,   fill=C_WHITE)
    draw.text((MARGIN, 78),  f"{date_str}（{weekday}）{session}",
              font=f_date, fill=(148, 163, 184))

    y = 148

    for color, sec_title, news_list, is_closed in news_sections:
        # Section bar
        draw.rectangle([(MARGIN, y), (MARGIN + 6, y + 34)], fill=color)
        draw.text((MARGIN + 18, y + 3), sec_title, font=f_sec, fill=color)
        y += 50

        if is_closed:
            draw.text((MARGIN + 10, y),
                      "• 今日休市，下週一開盤前請留意美股及外資動向",
                      font=f_news, fill=C_SUB)
            y += 44
        else:
            for idx, item in enumerate(news_list):
                # Badge
                bx, by = MARGIN, y + 3
                draw.ellipse([(bx, by), (bx + 26, by + 26)], fill=color)
                num_str = str(idx + 1)
                draw.text((bx + (13 - int(font_offset(num_str, f_num)/2)), by + 5),
                          num_str, font=f_num, fill=C_BADGE)

                tx = MARGIN + 38
                # Title
                lines = wrap_text(item['title'], f_news, CW - 48)
                for ln in lines:
                    draw.text((tx, y), ln, font=f_news, fill=C_TXT)
                    y += 32
                # Link
                if item.get('link'):
                    link_str = item['link']
                    if len(link_str) > 72:
                        link_str = link_str[:69] + '...'
                    draw.text((tx, y - 4), link_str, font=f_link, fill=C_LINK)
                    y += 26
                y += 16  # item gap

            # Thin divider after each news (not after last)
        y += 18  # section bottom gap

    # Divider before tips
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + 1)], fill=C_DIV)
    y += 14

    # Tips
    draw.text((MARGIN, y), "⚡ 注意事項", font=f_sec, fill=C_TXT)
    y += 44
    tips = [
        "台股交易時間：09:00–13:30",
        "留意三大法人買賣超動向",
        "重大消息 → 公開資訊觀測站 mops.twse.com.tw",
    ]
    for t in tips:
        draw.text((MARGIN + 10, y), f"• {t}", font=f_tip, fill=C_SUB)
        y += 32
    y += 16

    # Footer
    draw.rectangle([(0, H - 58), (W, H)], fill=C_HDR)
    draw.text((MARGIN, H - 40),
              "📚 資料來源：鉅亨網 RSS  ·  cnyes.com",
              font=f_foot, fill=(100, 116, 139))

    return img

def font_offset(text, font):
    try:
        return font.getlength(text)
    except Exception:
        return len(text) * 10

# ── 組裝資料 ──────────────────────────────────────────────────────────────────
closed_tw = (not is_weekday)
sections = [
    (C_TW,  "🇹🇼 台股重點新聞",   tw_news,  closed_tw),
    (C_US,  "🌏 美股 / 國際市場",  us_news,  False),
    (C_MAC, "📊 總體經濟",          mac_news, False),
]

img = generate_image(sections)

# ── 存成 BytesIO ──────────────────────────────────────────────────────────────
buf = io.BytesIO()
img.save(buf, format='PNG', optimize=True)
buf.seek(0)

# ── 推送 Telegram ─────────────────────────────────────────────────────────────
token   = os.environ["TELEGRAM_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

caption = f"📈 {date_str}（{weekday}）{session}\n資料來源：鉅亨網 RSS"

resp = requests.post(
    f"https://api.telegram.org/bot{token}/sendPhoto",
    data={"chat_id": chat_id, "caption": caption},
    files={"photo": ("briefing.png", buf, "image/png")}
)

if resp.json().get("ok"):
    print(f"✅ 圖片推播成功（{session}）")
else:
    print(f"❌ 推播失敗：{resp.text}")
    exit(1)
