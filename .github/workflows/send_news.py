#!/usr/bin/env python3
"""
每日財經簡報
第1則：市場資金動向分析（即時數據自動生成）
第2則：重點新聞連結
"""

import os
from datetime import datetime, timezone, timedelta
import requests, feedparser

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

TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}, timeout=30
    )
    print("send:", "OK" if r.json().get("ok") else r.text[:120])

# ── Yahoo Finance ─────────────────────────────────────────────────────────────
def yf(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        d = requests.get(url, headers=HEADERS, timeout=12).json()
        meta = d['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice') or 0
        prev  = meta.get('previousClose') or meta.get('chartPreviousClose') or price
        chg   = price - prev
        pct   = chg / prev * 100 if prev else 0
        return {'p': round(price, 2), 'chg': round(chg, 2), 'pct': round(pct, 2)}
    except Exception:
        return None

def arrow(d): return "▲" if d and d['chg'] >= 0 else "▼"
def s(v): return f"+{v}" if v >= 0 else str(v)

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
    except Exception:
        return None

def amt(n):
    if n is None: return '－'
    return f"{'+' if n>0 else ''}{n/1e8:.0f}億"

def inst_summary(inst):
    if not inst: return None
    f = inst.get('foreign')
    t = inst.get('trust')
    d = inst.get('dealer')
    total = (f or 0) + (t or 0) + (d or 0)
    parts = []
    if f is not None: parts.append(f"外資 {amt(f)}")
    if t is not None: parts.append(f"投信 {amt(t)}")
    if d is not None: parts.append(f"自營商 {amt(d)}")
    direction = "買超" if total > 0 else "賣超"
    return {'text': ' / '.join(parts), 'total': total, 'direction': direction,
            'foreign': f, 'trust': t, 'dealer': d}

# ── RSS ───────────────────────────────────────────────────────────────────────
def rss(url, n=6):
    try:
        feed = feedparser.parse(url)
        out  = []
        for e in feed.entries[:n]:
            t = e.get('title','').strip()
            l = e.get('link','').strip()
            if t: out.append({'t': t, 'l': l})
        return out
    except Exception:
        return []

tw_rss  = rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 6)
us_rss  = rss("https://www.cnyes.com/rss/cat/us_stock.xml", 6)
mac_rss = rss("https://www.cnyes.com/rss/cat/economy.xml",  5)
udn_rss = rss("https://money.udn.com/rssfeed/news/1/5607?ch=money", 5)

seen = set()
tw_all = []
for n in tw_rss + udn_rss:
    if n['t'] not in seen:
        seen.add(n['t'])
        tw_all.append(n)

# ── 抓數據 ────────────────────────────────────────────────────────────────────
taiex = yf("%5ETWII")
tsmc  = yf("2330.TW")
hon   = yf("2317.TW")
nvidia= yf("NVDA")
dji   = yf("%5EDJI")
spx   = yf("%5EGSPC")
ixic  = yf("%5EIXIC")
dxy   = yf("DX-Y.NYB")
t10y  = yf("%5ETNX")
t30y  = yf("%5ETYX")
inst  = get_inst()
ins   = inst_summary(inst)

# ════════════════════════════════════════════════════════════════════════════
# 第一則：市場資金動向分析
# ════════════════════════════════════════════════════════════════════════════
L = []
L.append(f"📈 市場資金動向週報｜{date_str}（{weekday}）\n")

# ─ 台股 ─────────────────────────────────────────────────────────────────────
if not is_weekday:
    L.append("🇹🇼 台股市場（今日休市）")
    L.append("本週累計表現請留意週一開盤動向，關注美股收盤與外資動態。\n")
else:
    L.append("🇹🇼 台股市場\n")

    # ① 加權指數
    if taiex:
        p, chg, pct = taiex['p'], taiex['chg'], taiex['pct']
        trend = ("強勢上攻" if pct > 1.5 else "穩步走高" if pct > 0.3
                 else "小幅震盪" if pct > -0.3 else "拉回修正" if pct > -1.5 else "明顯走弱")
        L.append(
            f"① 加權指數{trend}，收 {p:,.0f} 點（{arrow(taiex)}{abs(pct):.2f}%）\n"
            f"加權指數今日收 {p:,.0f} 點，{arrow(taiex)} {abs(chg):.0f} 點（{s(pct)}%）。"
            f"{'AI 供應鏈題材持續發酵，外資買盤支撐指數走高。' if chg>0 else '短線賣壓湧現，留意支撐能否守穩，觀察外資是否回補。'}\n"
        )

    # ② 三大法人
    if ins:
        f_dir = "買超" if (ins['foreign'] or 0) > 0 else "賣超"
        L.append(
            f"② 外資{f_dir} {amt(ins['foreign'])}，三大法人合計{ins['direction']} {amt(ins['total'])}\n"
            f"今日三大法人：{ins['text']}。"
            f"{'外資持續買超，籌碼面支撐多頭格局，法人動向有利後市。' if (ins['foreign'] or 0)>0 else '外資單日轉賣超，短線籌碼鬆動，留意指數支撐位是否守穩。'}\n"
        )
    else:
        cap_news = next((n for n in tw_all if any(k in n['t'] for k in ['外資','法人','買超','賣超','籌碼'])), None)
        if cap_news:
            L.append(f"② {cap_news['t']}\n法人動向為今日盤面觀察重點，影響後市多空方向。\n")

    # ③ 重點個股
    stock_parts = []
    if tsmc: stock_parts.append(f"台積電(2330) {tsmc['p']:,.0f} 元（{s(tsmc['pct'])}%）")
    if hon:  stock_parts.append(f"鴻海(2317) {hon['p']:,.0f} 元（{s(hon['pct'])}%）")
    if stock_parts:
        combined = tsmc['chg'] + (hon['chg'] if hon else 0) if tsmc else 0
        L.append(
            f"③ 台積電、鴻海 AI 供應鏈動向\n"
            + "；".join(stock_parts) + "。"
            f"{'外資持續鎖碼 AI 伺服器供應鏈，半導體族群籌碼集中效應明顯。' if combined>=0 else '權值股拉回，留意是否為短線整理或趨勢反轉訊號。'}\n"
        )

    # ④ 財報/題材新聞
    ear_news = next((n for n in tw_all if any(k in n['t'] for k in ['財報','業績','EPS','獲利','營收','法說'])), None)
    ben_news = next((n for n in tw_all if any(k in n['t'] for k in ['受惠','利多','漲停','創高','AI','半導體','輝達','黃仁勳'])), None)
    if ear_news:
        L.append(f"④ {ear_news['t']}\n業績表現為近期股價走勢關鍵驅動力，財報優於預期可望帶動股價上修。\n")
    elif ben_news:
        L.append(f"④ {ben_news['t']}\n題材股持續獲資金青睞，留意籌碼是否持續集中。\n")

# ─ 美股 ─────────────────────────────────────────────────────────────────────
L.append("\n🌏 美股市場\n")

# ① 三大指數
idx_parts = []
if dji:  idx_parts.append(f"道瓊 {dji['p']:,.0f}（{s(dji['pct'])}%）")
if spx:  idx_parts.append(f"標普500 {spx['p']:,.0f}（{s(spx['pct'])}%）")
if ixic: idx_parts.append(f"那斯達克 {ixic['p']:,.0f}（{s(ixic['pct'])}%）")
if idx_parts:
    base = dji or spx
    up   = base and base['chg'] >= 0
    L.append(
        f"① 美股三大指數{'走高' if up else '收低'}，最新報價\n"
        + " / ".join(idx_parts) + "。"
        f"{'AI 題材延燒＋地緣政治風險降溫，多頭氣氛延續。' if up else 'Fed 利率疑慮與獲利了結賣壓，盤面承壓。'}\n"
    )

# ② NVIDIA / 科技資金
if nvidia:
    L.append(
        f"② NVIDIA(NVDA) {nvidia['p']:,.2f} 美元（{s(nvidia['pct'])}%）\n"
        f"輝達股價{'走強，AI 伺服器需求旺盛，帶動台灣供應鏈相關個股同步受惠。' if nvidia['chg']>=0 else '拉回，留意是否影響台灣 AI 供應鏈族群連帶修正。'}\n"
    )
else:
    us_hot = next((n for n in us_rss if any(k in n['t'] for k in ['AI','輝達','NVIDIA','科技','半導體'])), us_rss[1] if len(us_rss)>1 else None)
    if us_hot:
        L.append(f"② {us_hot['t']}\nAI 及科技股動向牽動市場資金流向，影響台灣相關供應鏈。\n")

# ③ 美股資金/財報
us_ear = next((n for n in us_rss if any(k in n['t'] for k in ['財報','業績','EPS','獲利'])), None)
us_cap = next((n for n in us_rss if any(k in n['t'] for k in ['資金','法人','機構','基金','ETF'])), None)
us_pick = us_ear or us_cap or (us_rss[2] if len(us_rss)>2 else None)
if us_pick:
    L.append(f"③ {us_pick['t']}\n重點財報及機構資金動向為下週盤面關鍵觀察指標。\n")

# ─ 總體經濟 ──────────────────────────────────────────────────────────────────
L.append("\n📊 總體經濟 / 全球資金\n")

# ① 美元指數
if dxy:
    dxy_trend = "走強" if dxy['chg'] >= 0 else "走弱"
    L.append(
        f"① 美元指數 {dxy['p']:.1f}（{arrow(dxy)}{abs(dxy['pct']):.2f}%），{dxy_trend}\n"
        f"美元指數報 {dxy['p']:.1f}，{'避險買盤升溫，新興市場資金承壓，留意台幣匯率動向。' if dxy['chg']>=0 else '美元走弱，風險偏好回升，資金流向新興市場與風險資產。'}\n"
    )

# ② 美債殖利率
if t10y and t30y:
    spread = round(t30y['p'] - t10y['p'], 3)
    L.append(
        f"② 美債殖利率：10Y {t10y['p']:.3f}% / 30Y {t30y['p']:.3f}%\n"
        f"10 年期公債殖利率 {t10y['p']:.3f}%（{arrow(t10y)}{abs(t10y['pct']):.2f}%），30 年期 {t30y['p']:.3f}%，利差 {spread}%。"
        f"{'殖利率走升，對科技成長股估值形成壓力，關注 Fed 官員最新表態。' if t10y['chg']>0 else '殖利率回落，有利高估值成長股估值修復，市場風險偏好轉佳。'}\n"
    )

# ③ 總經新聞
mac_pick = next((n for n in mac_rss if any(k in n['t'] for k in ['Fed','聯準','降息','通膨','CPI','PMI','GDP','就業'])), mac_rss[0] if mac_rss else None)
if mac_pick:
    L.append(f"③ {mac_pick['t']}\nFed 政策方向與通膨數據持續左右全球資金配置，為當前最重要總體觀察指標。\n")

# ─ 注意事項 ──────────────────────────────────────────────────────────────────
L.append("⚡ 今日注意事項")
if is_morning and is_weekday:
    L.append("• 台股交易時間：09:00–13:30")
    L.append("• 留意外資開盤方向及三大法人動態")
elif is_weekday:
    L.append("• 今日收盤，關注三大法人最終買賣超結算")
    L.append("• 留意美股開盤方向及亞股盤後走勢")
else:
    L.append("• 週末休市，留意美股收盤及下週開盤觀察重點")
L.append("• 美債殖利率走勢牽動科技股估值，須持續追蹤")
L.append("• 重大消息請至公開資訊觀測站確認：mops.twse.com.tw")
L.append("\n📚 資料來源：Yahoo Finance / 台灣證券交易所 / 鉅亨網")

# ════════════════════════════════════════════════════════════════════════════
# 第二則：重點新聞連結
# ════════════════════════════════════════════════════════════════════════════
NUMS = "①②③④⑤"

def news_block(emoji_title, items, max_n=5):
    lines = [emoji_title]
    for i, n in enumerate(items[:max_n]):
        lines.append(f"{NUMS[i]} {n['t']}")
        if n.get('l'): lines.append(f"   {n['l']}")
    return '\n'.join(lines)

R = []
R.append(f"📈 每日財經簡報｜{date_str}（{weekday}）{session}\n")

if not is_weekday:
    R.append("🇹🇼 台股重點新聞（今日休市）")
    R.append("   https://www.cnyes.com/twstock/\n")
else:
    R.append(news_block("🇹🇼 台股重點新聞", tw_all[:5]))
    R.append("")

R.append(news_block("🌏 美股重點新聞", us_rss[:4]))
R.append("")
R.append(news_block("📊 總體經濟", mac_rss[:3]))
R.append("")
R.append("⚡ 盤後注意事項")
R.append("• 留意三大法人今日買賣超方向")
R.append("• 下週重點：美國就業報告、重量級企業財報")
R.append("• 公告查詢：https://mops.twse.com.tw")
R.append("\n📚 資料來源：鉅亨網 / 聯合新聞網 / 臺灣證券交易所")

# ── 發送 ──────────────────────────────────────────────────────────────────────
print("── 第一則：市場分析 ──")
send("\n".join(L))

print("── 第二則：新聞連結 ──")
send("\n".join(R))

print("✅ 完成")
