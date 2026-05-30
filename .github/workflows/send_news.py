#!/usr/bin/env python3
"""
每日財經簡報 — 三段推送：
  1. sendMessage  — 重點摘要
  2. sendMessage  — 新聞連結清單
  3. sendDocument — A4 PDF 簡報檔
"""

import os, io, textwrap
from datetime import datetime, timezone, timedelta
import requests, feedparser

# ── 時間 ──────────────────────────────────────────────────────────────────────
tz       = timezone(timedelta(hours=8))
now      = datetime.now(tz)
date_str = now.strftime("%Y/%m/%d")
weekday  = ["週一","週二","週三","週四","週五","週六","週日"][now.weekday()]
hour     = now.hour
is_morning = hour < 14
is_weekday = now.weekday() < 5
session    = "早盤簡報" if is_morning else "收盤復盤"

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

# ── Telegram helper ───────────────────────────────────────────────────────────
TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BASE    = f"https://api.telegram.org/bot{TOKEN}"

def send_message(text):
    r = requests.post(f"{BASE}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text})
    ok = r.json().get("ok")
    print("sendMessage:", "OK" if ok else r.text)
    return ok

def send_document(file_bytes, filename, caption=""):
    r = requests.post(
        f"{BASE}/sendDocument",
        data={"chat_id": CHAT_ID, "caption": caption},
        files={"document": (filename, file_bytes, "application/pdf")}
    )
    ok = r.json().get("ok")
    print("sendDocument:", "OK" if ok else r.text)
    return ok

# ════════════════════════════════════════════════════════════════════════════
# 第一則：重點摘要
# ════════════════════════════════════════════════════════════════════════════
def build_summary():
    lines = [f"📈 每日財經簡報｜{date_str}（{weekday}）{session}\n"]

    if not is_weekday:
        lines.append("🇹🇼 台股今日休市（週末）")
    else:
        lines.append("🇹🇼 台股重點摘要")
        for i, n in enumerate(tw_news, 1):
            lines.append(f"  {i}. {n['title']}")

    lines.append("")
    lines.append("🌏 美股 / 國際市場")
    for i, n in enumerate(us_news, 1):
        lines.append(f"  {i}. {n['title']}")

    lines.append("")
    lines.append("📊 總體經濟")
    for i, n in enumerate(mac_news, 1):
        lines.append(f"  {i}. {n['title']}")

    lines.append("")
    if is_morning:
        lines.append("⚡ 開盤前注意")
        lines.append("  • 台股交易時間：09:00–13:30")
        lines.append("  • 留意三大法人開盤動向")
    else:
        lines.append("⚡ 盤後注意")
        lines.append("  • 留意三大法人今日買賣超")
        lines.append("  • 關注美股期貨與亞股走勢")

    return "\n".join(lines)

# ════════════════════════════════════════════════════════════════════════════
# 第二則：新聞連結清單
# ════════════════════════════════════════════════════════════════════════════
def build_links():
    lines = [f"🔗 今日重點新聞連結｜{date_str}\n"]

    if not is_weekday:
        lines.append("🇹🇼 台股今日休市")
    else:
        lines.append("🇹🇼 台股")
        for i, n in enumerate(tw_news, 1):
            lines.append(f"  {i}. {n['title']}")
            if n.get('link'):
                lines.append(f"     {n['link']}")
    lines.append("")

    lines.append("🌏 美股 / 國際市場")
    for i, n in enumerate(us_news, 1):
        lines.append(f"  {i}. {n['title']}")
        if n.get('link'):
            lines.append(f"     {n['link']}")
    lines.append("")

    lines.append("📊 總體經濟")
    for i, n in enumerate(mac_news, 1):
        lines.append(f"  {i}. {n['title']}")
        if n.get('link'):
            lines.append(f"     {n['link']}")

    return "\n".join(lines)

# ════════════════════════════════════════════════════════════════════════════
# 第三則：PDF 簡報
# ════════════════════════════════════════════════════════════════════════════
def build_pdf():
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    # 字型路徑（Ubuntu GitHub Actions）
    FONT_PATHS = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf',
        '/usr/share/fonts/noto-cjk/NotoSansCJKtc-Regular.otf',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msjh.ttc',
    ]
    font_path = None
    for p in FONT_PATHS:
        if os.path.exists(p):
            font_path = p
            break

    buf = io.BytesIO()
    W, H = A4  # 595 x 841 pt
    c = rl_canvas.Canvas(buf, pagesize=A4)

    if font_path:
        pdfmetrics.registerFont(TTFont('CJK', font_path))
        FONT = 'CJK'
    else:
        FONT = 'Helvetica'

    MARGIN  = 36
    CW      = W - MARGIN * 2

    # ── 色塊定義
    HDR_COLOR  = colors.HexColor('#0F1726')
    TW_COLOR   = colors.HexColor('#DC2626')
    US_COLOR   = colors.HexColor('#2563EB')
    MAC_COLOR  = colors.HexColor('#059669')
    LINK_COLOR = colors.HexColor('#3B82F6')
    BG_COLOR   = colors.HexColor('#F8F9FC')
    SUB_COLOR  = colors.HexColor('#64748B')

    def wrap(text, font, size, max_w):
        """按像素寬度換行（中文適用）"""
        lines, cur = [], ''
        for ch in text:
            test = cur + ch
            c.setFont(font, size)
            if c.stringWidth(test, font, size) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
        return lines if lines else ['']

    # ── 頁面背景
    c.setFillColor(BG_COLOR)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Header
    c.setFillColor(HDR_COLOR)
    c.rect(0, H - 72, W, 72, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(FONT, 22)
    c.drawString(MARGIN, H - 34, f"每日財經簡報  {date_str}（{weekday}）{session}")
    c.setFont(FONT, 11)
    c.setFillColor(colors.HexColor('#94A3B8'))
    c.drawString(MARGIN, H - 56, "資料來源：鉅亨網 RSS  ·  cnyes.com")

    y = H - 92  # 起始 y（從 Header 下方）

    # ── 繪製一個 section
    def draw_section(color, title, news_list, closed=False):
        nonlocal y
        # Section header bar
        c.setFillColor(color)
        c.rect(MARGIN, y - 4, 5, 22, fill=1, stroke=0)
        c.setFont(FONT, 14)
        c.drawString(MARGIN + 12, y, title)
        y -= 26

        if closed:
            c.setFont(FONT, 11)
            c.setFillColor(SUB_COLOR)
            c.drawString(MARGIN + 8, y, "今日休市，下週一開盤前請留意美股及外資動向")
            y -= 20
            return

        for idx, item in enumerate(news_list):
            # Badge
            c.setFillColor(color)
            c.circle(MARGIN + 8, y + 5, 8, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont(FONT, 9)
            c.drawCentredString(MARGIN + 8, y + 2, str(idx + 1))

            tx = MARGIN + 22
            # Title
            title_lines = wrap(item['title'], FONT, 11, CW - 28)
            c.setFillColor(colors.HexColor('#0F1726'))
            c.setFont(FONT, 11)
            for ln in title_lines:
                c.drawString(tx, y, ln)
                y -= 16
                if y < 60:
                    c.showPage()
                    c.setFillColor(BG_COLOR)
                    c.rect(0, 0, W, H, fill=1, stroke=0)
                    y = H - 40

            # Link
            if item.get('link'):
                link_str = item['link']
                if len(link_str) > 80:
                    link_str = link_str[:77] + '...'
                c.setFillColor(LINK_COLOR)
                c.setFont(FONT, 9)
                c.drawString(tx, y, link_str)
                y -= 14

            y -= 8  # item gap

        y -= 10  # section gap

    sections = [
        (TW_COLOR,  "台股重點新聞",   tw_news,  not is_weekday),
        (US_COLOR,  "美股 / 國際市場", us_news,  False),
        (MAC_COLOR, "總體經濟",        mac_news, False),
    ]
    for col, ttl, news, closed in sections:
        draw_section(col, ttl, news, closed)

    # ── 注意事項
    y -= 4
    c.setStrokeColor(colors.HexColor('#E2E8F0'))
    c.line(MARGIN, y, W - MARGIN, y)
    y -= 14
    c.setFillColor(colors.HexColor('#0F1726'))
    c.setFont(FONT, 13)
    c.drawString(MARGIN, y, "注意事項")
    y -= 18
    tips = [
        "台股交易時間：09:00–13:30",
        "留意三大法人買賣超動向",
        "重大消息請至公開資訊觀測站確認  mops.twse.com.tw",
    ]
    for t in tips:
        c.setFont(FONT, 10)
        c.setFillColor(SUB_COLOR)
        c.drawString(MARGIN + 8, y, f"•  {t}")
        y -= 16

    # ── Footer
    c.setFillColor(HDR_COLOR)
    c.rect(0, 0, W, 28, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#64748B'))
    c.setFont(FONT, 9)
    c.drawString(MARGIN, 10, f"每日財經簡報  {date_str}  |  Generated by FinBot")

    c.save()
    buf.seek(0)
    return buf.read()

# ════════════════════════════════════════════════════════════════════════════
# 執行三段推送
# ════════════════════════════════════════════════════════════════════════════
print("── 第一則：重點摘要 ──")
send_message(build_summary())

print("── 第二則：新聞連結 ──")
send_message(build_links())

print("── 第三則：PDF 簡報 ──")
pdf_bytes = build_pdf()
send_document(
    pdf_bytes,
    filename=f"財經簡報_{date_str.replace('/', '')}.pdf",
    caption=f"📎 {date_str}（{weekday}）{session} 完整簡報"
)
