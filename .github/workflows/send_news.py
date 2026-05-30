#!/usr/bin/env python3
"""
每日財經簡報
第1則：市場分析（即時數據 + RSS 文章摘要）
第2則：重點新聞連結
"""

import os, re
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
month_str  = now.strftime("%m月")

TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}, timeout=30
    )
    print("send:", "OK" if r.json().get("ok") else r.text[:120])

# ── 清理 HTML ─────────────────────────────────────────────────────────────────
def clean(text):
    text = re.sub(r'<[^>]+>', '', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:200]  # 最多200字

# ── Yahoo Finance ─────────────────────────────────────────────────────────────
def yf(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo"
        d = requests.get(url, headers=HEADERS, timeout=12).json()
        result = d['chart']['result'][0]
        meta   = result['meta']
        price  = meta.get('regularMarketPrice') or 0
        prev   = meta.get('previousClose') or meta.get('chartPreviousClose') or price
        chg    = price - prev
        pct    = chg / prev * 100 if prev else 0
        # 月初價格（取第一個收盤價）
        closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
        month_open = next((c for c in closes if c), price)
        month_chg  = price - month_open
        month_pct  = month_chg / month_open * 100 if month_open else 0
        return {'p': round(price,2), 'chg': round(chg,2), 'pct': round(pct,2),
                'mp': round(month_open,2), 'mchg': round(month_chg,2), 'mpct': round(month_pct,2)}
    except Exception:
        return None

def s(v): return f"+{v}" if v >= 0 else str(v)
def arrow(d): return "▲" if d and d['chg'] >= 0 else "▼"
def marrow(d): return "▲" if d and d['mchg'] >= 0 else "▼"

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

def amt(n, unit='億'):
    if n is None: return '－'
    v = n / (1e8 if unit=='億' else 1e12)
    return f"{'+' if n>0 else ''}{v:.0f}{unit}"

# ── RSS（含摘要）────────────────────────────────────────────────────────────
def rss(url, n=8):
    try:
        feed = feedparser.parse(url)
        out  = []
        for e in feed.entries[:n]:
            t   = e.get('title','').strip()
            l   = e.get('link','').strip()
            # 取文章摘要（summary > description > content）
            raw = (e.get('summary') or e.get('description') or
                   (e.get('content',[{}])[0].get('value','') if e.get('content') else ''))
            sm  = clean(raw)
            if t:
                out.append({'t': t, 'l': l, 'sm': sm})
        return out
    except Exception:
        return []

# 多來源抓取
tw_rss   = rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 8)
us_rss   = rss("https://www.cnyes.com/rss/cat/us_stock.xml", 8)
mac_rss  = rss("https://www.cnyes.com/rss/cat/economy.xml",  6)
udn_rss  = rss("https://money.udn.com/rssfeed/news/1/5607?ch=money", 6)
inst_rss = rss("https://www.cnyes.com/rss/cat/tw_fund.xml", 5)  # 法人/外資

# 台股合併去重
seen = set()
tw_all = []
for n in tw_rss + udn_rss + inst_rss:
    if n['t'] not in seen:
        seen.add(n['t'])
        tw_all.append(n)

# 分類
def pick(pool, kws, n=3):
    found = [x for x in pool if any(k in x['t'] for k in kws)]
    return found[:n] if found else pool[:n]

tw_cap  = pick(tw_all, ['外資','法人','買超','賣超','籌碼','三大法人','投信','自營'])
tw_ear  = pick(tw_all, ['財報','業績','EPS','獲利','營收','淨利','法說','展望'])
tw_ben  = pick(tw_all, ['受惠','利多','漲停','創高','AI','半導體','輝達','黃仁勳','供應鏈','題材'])
us_cap  = pick(us_rss,  ['資金','外資','機構','法人','ETF','基金'])
us_ear  = pick(us_rss,  ['財報','業績','EPS','獲利'])
us_hot  = pick(us_rss,  ['AI','輝達','NVIDIA','科技','半導體','漲','創高'])
mac_key = pick(mac_rss, ['Fed','聯準','降息','升息','通膨','CPI','PMI','GDP','就業','利率'])

# ── 抓即時數據 ────────────────────────────────────────────────────────────────
taiex  = yf("%5ETWII")
tsmc   = yf("2330.TW")
hon    = yf("2317.TW")
nvidia = yf("NVDA")
dji    = yf("%5EDJI")
spx    = yf("%5EGSPC")
ixic   = yf("%5EIXIC")
dxy    = yf("DX-Y.NYB")
t10y   = yf("%5ETNX")
t30y   = yf("%5ETYX")
inst   = get_inst()

# ══════════════════════════════════════════════════════════════════════════════
# 第一則：市場資金動向分析
# ══════════════════════════════════════════════════════════════════════════════
L = []
L.append(f"📈 市場資金動向週報｜{date_str}（{weekday}）\n")

# ─ 台股 ─────────────────────────────────────────────────────────────────────
if not is_weekday:
    L.append("🇹🇼 台股市場（今日休市）\n")
    if tw_all:
        n = tw_all[0]
        sm = n['sm'] if n['sm'] else "下週一開盤前請留意美股及外資動向。"
        L.append(f"① {n['t']}\n{sm}\n")
else:
    L.append("🇹🇼 台股市場\n")

    # ① 加權指數 + 本月表現
    if taiex:
        p, chg, pct   = taiex['p'], taiex['chg'], taiex['pct']
        mchg, mpct    = taiex['mchg'], taiex['mpct']
        trend = ("強勢上攻" if pct>1.5 else "穩步走高" if pct>0.3
                 else "小幅震盪" if pct>-0.3 else "拉回修正" if pct>-1.5 else "明顯走弱")
        month_context = f"{month_str}以來{'累計上漲' if mchg>=0 else '累計下跌'} {abs(mpct):.1f}%（{marrow(taiex)}{abs(mchg):.0f} 點）。"
        L.append(
            f"① 加權指數{trend}，收 {p:,.0f} 點（{arrow(taiex)}{abs(pct):.2f}%）\n"
            f"加權指數今日收 {p:,.0f} 點，{arrow(taiex)} {abs(chg):.0f} 點（{s(pct)}%）。{month_context}"
            f"{'AI 供應鏈題材持續發酵，外資買盤支撐指數走高。' if chg>0 else '短線賣壓出籠，留意支撐是否守穩。'}\n"
        )
    elif tw_ben:
        n = tw_ben[0]
        sm = n['sm'] if n['sm'] else "請至 Yahoo股市查看今日加權指數表現。"
        L.append(f"① {n['t']}\n{sm}\n")

    # ② 三大法人（即時數據優先，無則用新聞摘要）
    if inst and any(v is not None for v in inst.values()):
        f = inst.get('foreign'); t = inst.get('trust'); d = inst.get('dealer')
        total = (f or 0) + (t or 0) + (d or 0)
        parts = []
        if f is not None: parts.append(f"外資 {amt(f)}")
        if t is not None: parts.append(f"投信 {amt(t)}")
        if d is not None: parts.append(f"自營商 {amt(d)}")
        f_dir = "買超" if (f or 0)>0 else "賣超"
        t_dir = "合計買超" if total>0 else "合計賣超"
        L.append(
            f"② 外資{f_dir} {amt(f)}，三大法人{t_dir} {amt(total)}\n"
            f"今日三大法人：{' / '.join(parts)}。"
            f"{'外資持續買超，籌碼面支撐多頭格局。' if (f or 0)>0 else '外資單日轉賣超，短線籌碼鬆動，留意支撐位。'}"
        )
        # 補充法人新聞摘要
        if tw_cap and tw_cap[0]['sm']:
            L.append(f"\n延伸：{tw_cap[0]['sm']}\n")
        else:
            L.append("\n")
    elif tw_cap:
        n = tw_cap[0]
        sm = n['sm'] if n['sm'] else "三大法人買賣超為今日盤面觀察重點。"
        L.append(f"② {n['t']}\n{sm}\n")

    # ③ 重點個股
    stock_parts = []
    if tsmc:
        minfo = f"，本月{'+' if tsmc['mpct']>=0 else ''}{tsmc['mpct']:.1f}%"
        stock_parts.append(f"台積電(2330) {tsmc['p']:,.0f} 元（{arrow(tsmc)}{abs(tsmc['pct']):.2f}%{minfo}）")
    if hon:
        stock_parts.append(f"鴻海(2317) {hon['p']:,.0f} 元（{arrow(hon)}{abs(hon['pct']):.2f}%）")
    if stock_parts:
        combined_up = (tsmc and tsmc['chg']>=0) or (hon and hon['chg']>=0)
        L.append(
            f"③ AI 供應鏈權值股表現\n"
            + "\n".join(stock_parts) + "。\n"
            f"{'外資持續增持 AI 供應鏈，台積電籌碼鎖定效應明顯，半導體族群動能強勁。' if combined_up else '權值股短線拉回，留意是否為整理或趨勢轉折訊號。'}\n"
        )

    # ④ 財報或題材深度新聞（附摘要）
    deep = None
    if tw_ear: deep = tw_ear[0]
    elif tw_ben and len(tw_ben)>1: deep = tw_ben[1]
    if deep:
        sm = deep['sm'] if deep['sm'] else "詳細內容請見連結。"
        L.append(f"④ {deep['t']}\n{sm}\n")

# ─ 美股 ─────────────────────────────────────────────────────────────────────
L.append("\n🌏 美股市場\n")

# ① 三大指數
idx_parts = []
if dji:  idx_parts.append(f"道瓊 {dji['p']:,.0f}（{s(dji['pct'])}%）")
if spx:  idx_parts.append(f"標普500 {spx['p']:,.0f}（{s(spx['pct'])}%）")
if ixic: idx_parts.append(f"那斯達克 {ixic['p']:,.0f}（{s(ixic['pct'])}%）")
if idx_parts:
    base = dji or spx
    up = base and base['chg'] >= 0
    L.append(
        f"① 美股三大指數{'普漲，多頭氣氛延續' if up else '下跌，獲利了結賣壓出現'}\n"
        + " / ".join(idx_parts) + "。\n"
        f"{'AI 題材延燒、地緣政治風險降溫，資金持續流入美股。' if up else 'Fed 利率疑慮升溫，部分資金轉向防禦型資產。'}\n"
    )

# ② NVDA + 科技資金
if nvidia:
    nvda_up = nvidia['chg'] >= 0
    hot_news = us_hot[0] if us_hot else None
    sm = hot_news['sm'] if hot_news and hot_news['sm'] else ""
    L.append(
        f"② NVIDIA(NVDA) {nvidia['p']:,.2f} 美元（{arrow(nvidia)}{abs(nvidia['pct']):.2f}%），本月{s(nvidia['mpct'])}%\n"
        f"輝達{'強勁上漲，AI 伺服器需求爆發' if nvda_up else '拉回修正，短線獲利了結'}，"
        f"{'直接帶動台灣 AI 供應鏈族群同步受惠。' if nvda_up else '台灣相關供應鏈股票需留意連帶修正壓力。'}"
        f"{chr(10)+sm if sm else ''}\n"
    )
elif us_hot:
    n = us_hot[0]
    sm = n['sm'] if n['sm'] else ""
    L.append(f"② {n['t']}\n{sm}\n")

# ③ 財報/資金動向（附摘要）
us_pick = (us_ear[0] if us_ear else None) or (us_cap[0] if us_cap else None) or (us_rss[2] if len(us_rss)>2 else None)
if us_pick:
    sm = us_pick['sm'] if us_pick['sm'] else ""
    L.append(f"③ {us_pick['t']}\n{sm if sm else '重點財報及機構資金動向為下週盤面關鍵觀察指標。'}\n")

# ─ 總體經濟 ──────────────────────────────────────────────────────────────────
L.append("\n📊 總體經濟 / 全球資金\n")

# ① 美元指數
if dxy:
    L.append(
        f"① 美元指數 {dxy['p']:.1f}（{arrow(dxy)}{abs(dxy['pct']):.2f}%），本月{s(dxy['mpct'])}%\n"
        f"{'避險買盤升溫，新興市場資金面臨壓力，留意台幣匯率走向。' if dxy['chg']>=0 else '美元走弱，風險偏好回升，有利新興市場資產表現。'}\n"
    )

# ② 美債殖利率
if t10y and t30y:
    spread = round(t30y['p'] - t10y['p'], 3)
    L.append(
        f"② 美債殖利率：10Y {t10y['p']:.3f}%（{arrow(t10y)}{abs(t10y['pct']):.2f}%）/ 30Y {t30y['p']:.3f}%，利差 {spread:.2f}%\n"
        f"{'殖利率走升對成長股估值施壓，科技股需留意修正風險。' if t10y['chg']>0 else '殖利率回落，有利科技成長股估值修復，市場風險偏好轉佳。'}\n"
    )

# ③ 重點總經新聞（附摘要）
if mac_key:
    n = mac_key[0]
    sm = n['sm'] if n['sm'] else ""
    L.append(f"③ {n['t']}\n{sm if sm else 'Fed 政策方向與通膨數據持續左右全球資金配置。'}\n")
elif mac_rss:
    n = mac_rss[0]
    sm = n['sm'] if n['sm'] else ""
    L.append(f"③ {n['t']}\n{sm if sm else '總體經濟數據影響全球資金流向，請持續關注。'}\n")

# 注意事項
L.append("⚡ 今日注意事項")
if is_morning and is_weekday:
    L.append("• 台股交易時間：09:00–13:30")
    L.append("• 留意外資開盤方向及三大法人動態")
elif is_weekday:
    L.append("• 今日收盤，關注三大法人最終買賣超")
    L.append("• 留意美股開盤走向及亞股盤後動態")
else:
    L.append("• 週末休市，關注美股收盤及下週開盤觀察重點")
L.append("• 美債殖利率走勢牽動科技股估值，持續追蹤")
L.append("• 重大公告查詢：mops.twse.com.tw")
L.append("\n📚 資料來源：Yahoo Finance / 台灣證券交易所 / 鉅亨網 / 聯合新聞網")

# ══════════════════════════════════════════════════════════════════════════════
# 第二則：重點新聞連結
# ══════════════════════════════════════════════════════════════════════════════
NUMS = "①②③④⑤"

def news_block(title, items, max_n=5):
    lines = [title]
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
