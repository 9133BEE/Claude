#!/usr/bin/env python3
"""
每日財經簡報
第1則：市場資金動向分析（即時數據 + 文章摘要組合）
第2則：重點新聞連結
"""

import os, re, html
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
month_day  = now.strftime("%-m/%-d") if hasattr(now, 'strftime') else now.strftime("%m/%d").lstrip('0')

TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; finbot/1.0)'}

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}, timeout=30
    )
    print("send:", "OK" if r.json().get("ok") else r.text[:120])

# ── HTML 清理 ─────────────────────────────────────────────────────────────────
def clean(text, maxlen=300):
    if not text: return ''
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # 移除常見廢話前綴
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
    except Exception:
        return None

def s(v):    return f"+{v}" if v >= 0 else str(v)
def ar(d):   return "▲" if d and d['chg'] >= 0 else "▼"
def mar(d):  return "▲" if d and d['mchg'] >= 0 else "▼"
def amt(n):
    if n is None: return '－'
    return f"{'+' if n>0 else ''}{n/1e8:.0f}億"

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

# ── RSS（抓完整摘要）────────────────────────────────────────────────────────
def rss(url, n=10):
    try:
        feed = feedparser.parse(url)
        out  = []
        for e in feed.entries[:n]:
            t   = e.get('title', '').strip()
            lnk = e.get('link', '').strip()
            raw = (e.get('summary') or e.get('description') or
                   (e.get('content', [{}])[0].get('value', '') if e.get('content') else ''))
            sm  = clean(raw, 280)
            if t:
                out.append({'t': t, 'l': lnk, 'sm': sm})
        return out
    except Exception:
        return []

# 多來源抓取
tw1  = rss("https://www.cnyes.com/rss/cat/tw_stock.xml", 10)
tw2  = rss("https://money.udn.com/rssfeed/news/1/5607?ch=money", 8)
us1  = rss("https://www.cnyes.com/rss/cat/us_stock.xml", 10)
mac1 = rss("https://www.cnyes.com/rss/cat/economy.xml", 8)

# 台股去重合併
seen = set()
tw_all = []
for n in tw1 + tw2:
    if n['t'] not in seen:
        seen.add(n['t'])
        tw_all.append(n)

# 精選分類
def pick1(pool, kws):
    """取第一筆符合關鍵字且有摘要的新聞"""
    for n in pool:
        if any(k in n['t'] for k in kws) and n['sm']:
            return n
    for n in pool:
        if any(k in n['t'] for k in kws):
            return n
    return None

def pick_all(pool, kws, max_n=5):
    found = [n for n in pool if any(k in n['t'] for k in kws)]
    return found[:max_n]

# ── 即時數據 ──────────────────────────────────────────────────────────────────
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
# 組合第一則：市場資金動向分析
# ══════════════════════════════════════════════════════════════════════════════
L = [f"📈 市場資金動向週報｜{date_str}（{weekday}）\n"]

def add_point(num, headline, body):
    L.append(f"{num} {headline}")
    L.append(f"{body}\n")

# ─ 台股 ─────────────────────────────────────────────────────────────────────
L.append("🇹🇼 台股市場\n")

# ① 大盤指數
if taiex:
    p, chg, pct = taiex['p'], taiex['chg'], taiex['pct']
    mchg, mpct  = taiex['mchg'], taiex['mpct']
    trend = ("強勢上攻" if pct>1.5 else "穩步走高" if pct>0.3
             else "小幅震盪" if abs(pct)<=0.3 else "拉回修正" if pct>-1.5 else "明顯走弱")
    headline = f"加權指數{trend}，收 {p:,.0f} 點（{ar(taiex)}{abs(pct):.2f}%）"
    # 從新聞補充月度背景
    idx_news = pick1(tw_all, ['加權','大盤','指數','創高','新高','點關卡'])
    if idx_news and idx_news['sm']:
        body = (f"加權指數今日收 {p:,.0f} 點，{ar(taiex)} {abs(chg):.0f} 點（{s(pct)}%），"
                f"本月累計{mar(taiex)}{abs(mpct):.1f}%（{mar(taiex)}{abs(mchg):.0f} 點）。"
                f"{idx_news['sm']}")
    else:
        body = (f"加權指數今日收 {p:,.0f} 點，{ar(taiex)} {abs(chg):.0f} 點（{s(pct)}%），"
                f"本月累計{mar(taiex)}{abs(mpct):.1f}%。"
                f"{'AI 供應鏈題材持續發酵，外資買盤支撐指數走高。' if chg>0 else '短線賣壓出籠，留意支撐能否守穩。'}")
    add_point("①", headline, body)
else:
    n = pick1(tw_all, ['加權','大盤','指數'])
    if n:
        add_point("①", n['t'], n['sm'] or "請至 Yahoo 股市查看今日加權指數表現。")

# ② 三大法人
if inst and any(v is not None for v in inst.values()):
    f = inst.get('foreign'); t = inst.get('trust'); d = inst.get('dealer')
    total = (f or 0) + (t or 0) + (d or 0)
    f_dir = "買超" if (f or 0) > 0 else "賣超"
    t_dir = "合計買超" if total > 0 else "合計賣超"
    headline = f"外資{f_dir} {amt(f)}，三大法人{t_dir} {amt(total)}"
    parts = []
    if f is not None: parts.append(f"外資 {amt(f)}")
    if t is not None: parts.append(f"投信 {amt(t)}")
    if d is not None: parts.append(f"自營商 {amt(d)}")
    data_line = f"三大法人今日：{' / '.join(parts)}。"
    inst_news = pick1(tw_all, ['外資','法人','買超','賣超','籌碼','三大法人','投信'])
    body = data_line + (inst_news['sm'] if inst_news and inst_news['sm'] else
           ('外資持續買超，籌碼面支撐多頭格局，法人動向有利後市。' if (f or 0)>0
            else '外資單日轉賣超，短線籌碼鬆動，留意指數支撐位是否守穩。'))
    add_point("②", headline, body)
else:
    n = pick1(tw_all, ['外資','法人','買超','賣超','籌碼','三大法人'])
    if n:
        add_point("②", n['t'], n['sm'] or "三大法人動向為今日盤面重要觀察指標。")

# ③ 重點個股
if tsmc or hon:
    parts = []
    if tsmc: parts.append(f"台積電(2330) {tsmc['p']:,.0f} 元（{s(tsmc['pct'])}%），本月{s(tsmc['mpct'])}%")
    if hon:  parts.append(f"鴻海(2317) {hon['p']:,.0f} 元（{s(hon['pct'])}%）")
    headline = "台積電、鴻海 AI 供應鏈個股動向"
    stock_news = pick1(tw_all, ['台積電','鴻海','AI','半導體','供應鏈','輝達','黃仁勳'])
    body = ("；".join(parts) + "。\n" +
            (stock_news['sm'] if stock_news and stock_news['sm'] else
             ('外資持續鎖碼 AI 伺服器供應鏈，半導體族群籌碼集中效應明顯。'
              if (tsmc and tsmc['chg']>=0) else '權值股短線拉回，留意是否為整理或趨勢反轉。')))
    add_point("③", headline, body)
else:
    n = pick1(tw_all, ['台積電','鴻海','AI','半導體','供應鏈'])
    if n:
        add_point("③", n['t'], n['sm'] or "AI 供應鏈族群持續獲資金青睞。")

# ④ 財報或題材（用新聞摘要）
n = pick1(tw_all, ['財報','業績','EPS','獲利','營收','法說']) or \
    pick1(tw_all, ['受惠','利多','漲停','目標價','上調','題材'])
if n:
    add_point("④", n['t'], n['sm'] or "詳細內容請見連結。")

# ─ 美股 ─────────────────────────────────────────────────────────────────────
L.append("\n🌏 美股市場\n")

# ① 三大指數
parts = []
if dji:  parts.append(f"道瓊 {dji['p']:,.0f}（{s(dji['pct'])}%）")
if spx:  parts.append(f"標普500 {spx['p']:,.0f}（{s(spx['pct'])}%）")
if ixic: parts.append(f"那斯達克 {ixic['p']:,.0f}（{s(ixic['pct'])}%）")
if parts:
    base = dji or spx
    up   = base and base['chg'] >= 0
    headline = f"美股三大指數{'走高，多頭延續' if up else '收低，獲利了結'}"
    idx_news  = pick1(us1, ['盤後','收盤','道瓊','標普','那斯達克','三大指數'])
    body = " / ".join(parts) + "。\n" + (
        idx_news['sm'] if idx_news and idx_news['sm'] else
        ('AI 題材延燒、地緣政治風險降溫，資金持續流入美股。' if up
         else 'Fed 利率疑慮與獲利了結賣壓，盤面承壓。'))
    add_point("①", headline, body)

# ② 機構/資金動向
n = pick1(us1, ['機構','基金','資金','外資','ETF','法人','買進','賣出'])
if n:
    add_point("②", n['t'], n['sm'] or "機構資金動向為美股後市重要觀察指標。")
elif nvidia:
    nvda_up = nvidia['chg'] >= 0
    headline = f"NVIDIA(NVDA) {nvidia['p']:,.2f} 美元（{s(nvidia['pct'])}%），本月{s(nvidia['mpct'])}%"
    n2 = pick1(us1, ['AI','輝達','NVIDIA','科技','半導體'])
    body = (n2['sm'] if n2 and n2['sm'] else
            ('輝達強勁上漲，AI 伺服器需求爆發，帶動台灣供應鏈族群同步受惠。' if nvda_up
             else '輝達拉回，留意台灣 AI 供應鏈族群連帶修正壓力。'))
    add_point("②", headline, body)

# ③ 財報或題材
n = pick1(us1, ['財報','業績','EPS','獲利','IPO','法說']) or \
    pick1(us1, ['AI','半導體','科技','漲','創高','受惠'])
if n:
    add_point("③", n['t'], n['sm'] or "重點財報及題材股動向牽動市場情緒。")

# ─ 總體經濟 ──────────────────────────────────────────────────────────────────
L.append("\n📊 總體經濟 / 全球資金\n")

# ① Fed/利率
n = pick1(mac1, ['Fed','聯準','降息','升息','利率','FOMC','鮑爾','通膨','CPI'])
if n:
    add_point("①", n['t'], n['sm'] or "Fed 政策方向持續左右全球資金配置。")
elif dxy:
    add_point("①", f"美元指數 {dxy['p']:.1f}（{ar(dxy)}{abs(dxy['pct']):.2f}%）",
              f"{'避險買盤升溫，新興市場資金面臨壓力。' if dxy['chg']>=0 else '美元走弱，風險偏好回升，有利新興市場資產。'}")

# ② 美債
if t10y and t30y:
    spread = round(t30y['p'] - t10y['p'], 3)
    n = pick1(mac1, ['美債','殖利率','公債','債市','利差'])
    headline = f"美債殖利率：10Y {t10y['p']:.3f}% / 30Y {t30y['p']:.3f}%，利差 {spread:.2f}%"
    body = (n['sm'] if n and n['sm'] else
            ('殖利率走升，對科技成長股估值施壓。' if t10y['chg']>0
             else '殖利率回落，有利科技股估值修復。'))
    add_point("②", headline, body)
else:
    n = pick1(mac1, ['美債','殖利率','公債','債市'])
    if n:
        add_point("②", n['t'], n['sm'] or "美債殖利率為全球資金配置重要指標。")

# ③ 其他總經
used = set()
for n in mac1:
    if n['t'] not in used and any(k in n['t'] for k in ['GDP','PMI','就業','油價','黃金','匯率','美元','地緣']):
        add_point("③", n['t'], n['sm'] or "全球總體經濟動向持續影響市場風險偏好。")
        used.add(n['t'])
        break

# 注意事項
L.append("⚡ 今日注意事項")
if is_morning and is_weekday:
    L.append("• 台股交易時間：09:00–13:30")
    L.append("• 留意外資開盤方向及三大法人動態")
elif is_weekday:
    L.append("• 今日收盤，關注三大法人最終買賣超")
    L.append("• 留意美股開盤走向及亞股盤後動態")
else:
    L.append("• 週末休市，留意美股收盤及下週觀察重點")
L.append("• 美債殖利率走勢牽動科技股估值")
L.append("• 重大消息請至公開資訊觀測站確認")
L.append("\n📚 資料來源：鉅亨網 / Yahoo股市 / 臺灣證券交易所")

# ══════════════════════════════════════════════════════════════════════════════
# 第二則：重點新聞連結
# ══════════════════════════════════════════════════════════════════════════════
NUMS = "①②③④⑤"

def block(title, items, n=5):
    lines = [title]
    for i, x in enumerate(items[:n]):
        lines.append(f"{NUMS[i]} {x['t']}")
        if x.get('l'): lines.append(f"   {x['l']}")
    return "\n".join(lines)

R = [f"📈 每日財經簡報｜{date_str}（{weekday}）{session}\n"]

if not is_weekday:
    R.append("🇹🇼 台股重點新聞（今日休市）")
    R.append("   https://www.cnyes.com/twstock/\n")
else:
    R.append(block("🇹🇼 台股重點新聞", tw_all[:5]))
    R.append("")

R.append(block("🌏 美股重點新聞", us1[:4]))
R.append("")
R.append(block("📊 總體經濟", mac1[:3]))
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
