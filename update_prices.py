#!/usr/bin/env python3
"""
投資組合自動更新腳本 v2
台股：每個交易日 15:05（台灣時間）→ Yahoo Finance API
美股：每個交易日 06:00（台灣時間）→ Yahoo Finance API
基金：每個交易日 20:00（台灣時間）→ MoneyDJ
"""

import re, sys, time, json, datetime, urllib.request, urllib.error
from pathlib import Path

# ── 持倉設定 ──────────────────────────────────────────────
TW_STOCKS = {
    't631':  {'symbol':'00631L.TW', 'cost':29.93,  'shares':2000,  'ct':59860,   'name':'元大台灣50正2'},
    't922':  {'symbol':'00922.TW',  'cost':29.03,  'shares':11000, 'ct':319330,  'name':'國泰台灣領袖50'},
    't882':  {'symbol':'00882.TW',  'cost':12.68,  'shares':28000, 'ct':355040,  'name':'中信中國高股息'},
    't955':  {'symbol':'00955.TWO', 'cost':15.57,  'shares':20000, 'ct':311400,  'name':'中信日本商社'},
    't9816': {'symbol':'009816.TW', 'cost':10.25,  'shares':6000,  'ct':61500,   'name':'凱基台灣TOP50'},
    't990':  {'symbol':'00990A.TW', 'cost':11.84,  'shares':7000,  'ct':82880,   'name':'主動元大AI新經濟'},
    't2313': {'symbol':'2313.TW',   'cost':222.82, 'shares':1000,  'ct':222820,  'name':'華通電腦'},
    't2359': {'symbol':'2359.TW',   'cost':124.43, 'shares':2000,  'ct':248860,  'name':'所羅門'},
    't3481': {'symbol':'3481.TW',   'cost':25.39,  'shares':3000,  'ct':76170,   'name':'群創光電'},
    't6488': {'symbol':'6488.TWO',  'cost':656.93, 'shares':1000,  'ct':656930,  'name':'環球晶'},
    't8070': {'symbol':'8070.TWO',  'cost':43.06,  'shares':1000,  'ct':43060,   'name':'長華電材'},
}

US_STOCKS = {
    'ag':   {'symbol':'AG',   'cost':20.11,  'shares':110, 'ct':2212,  'name':'First Majestic'},
    'cohr': {'symbol':'COHR', 'cost':235.67, 'shares':6,   'ct':1414,  'name':'Coherent'},
    'tsm':  {'symbol':'TSM',  'cost':330.46, 'shares':6,   'ct':1983,  'name':'台積電ADR'},
    'tsla': {'symbol':'TSLA', 'cost':387.58, 'shares':5,   'ct':1938,  'name':'Tesla'},
    'uuuu': {'symbol':'UUUU', 'cost':20.86,  'shares':121, 'ct':2524,  'name':'Energy Fuels'},
    'eose': {'symbol':'EOSE', 'cost':7.83,   'shares':40,  'ct':313,   'name':'Eos Energy'},
    'nbis': {'symbol':'NBIS', 'cost':86.88,  'shares':3,   'ct':261,   'name':'Nebius'},
    'onds': {'symbol':'ONDS', 'cost':8.96,   'shares':20,  'ct':179,   'name':'Ondas'},
    'orcl': {'symbol':'ORCL', 'cost':161.24, 'shares':4,   'ct':645,   'name':'Oracle'},
}

FUNDS = {
    'f1':  {'name':'安聯智慧城市AMg', 'moneydj':'tlzm8', 'cost_usd':318.00,   'units':35.432},
    'f2':  {'name':'PIMCO強化月收息', 'moneydj':'pim91', 'cost_usd':50000.00, 'units':6226.65},
    'f3':  {'name':'PIMCO穩定月收息', 'moneydj':'pim90', 'cost_usd':36021.00, 'units':3748.283},
    'fai': {'name':'安聯AI AT USD',   'moneydj':'tlh43', 'cost_usd':1500.00,  'units':43.732},
    'flm': {'name':'美盛凱利基建',    'moneydj':'wea84', 'cost_usd':5000.00,  'units':236.831},
}

HTML_FILE = Path('portfolio_tracker_v3.html')

# ── Yahoo Finance API ──────────────────────────────────────
def fetch_yahoo(symbols):
    syms = ','.join(symbols)
    url = (f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={syms}'
           f'&fields=regularMarketPrice,regularMarketPreviousClose,'
           f'regularMarketChangePercent,shortName')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = {}
        for q in data.get('quoteResponse', {}).get('result', []):
            sym = q.get('symbol', '')
            results[sym] = {
                'price':  q.get('regularMarketPrice'),
                'chgPct': q.get('regularMarketChangePercent', 0),
            }
        return results
    except Exception as e:
        print(f'  ✗ Yahoo API 錯誤: {e}')
        return {}

# ── MoneyDJ 基金淨值 ──────────────────────────────────────
def fetch_fund_nav(code):
    url = f'https://www.moneydj.com/funddj/ya/yp010001.djhtm?a={code}'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'text/html',
        'Referer': 'https://www.moneydj.com/',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        m = re.search(r'(\d{4}/\d{2}/\d{2})[^<]*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>', html)
        if m:
            return {'nav': float(m.group(2)), 'date': m.group(1)}
    except Exception as e:
        print(f'  ✗ MoneyDJ {code} 錯誤: {e}')
    return None

# ── HTML 讀寫 ──────────────────────────────────────────────
def load():
    return HTML_FILE.read_text(encoding='utf-8')

def save(content):
    HTML_FILE.write_text(content, encoding='utf-8')

def tw_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

def fmt_date(dt):
    return dt.strftime('%Y/%m/%d')

def fmt_mmdd(dt):
    return dt.strftime('%-m/%-d') if sys.platform != 'win32' else dt.strftime('%m/%d').lstrip('0').replace('/0','/')

# ── 台股更新 ──────────────────────────────────────────────
def run_tw():
    now = tw_now()
    date_str = fmt_date(now)
    mmdd = now.strftime('%m/%d').lstrip('0').replace('/0','/')
    print(f'\n=== 台股更新 {date_str} ===')

    symbols = [d['symbol'] for d in TW_STOCKS.values()]
    raw = fetch_yahoo(symbols)

    prices = {}
    for tid, d in TW_STOCKS.items():
        info = raw.get(d['symbol'])
        if info and info.get('price'):
            prices[tid] = info['price']
            mv = info['price'] * d['shares']
            pnl = mv - d['ct']
            print(f"  ✓ {d['symbol']:15} ${info['price']:.2f} ({info['chgPct']:+.2f}%) 損益NT${pnl:+,.0f}")
        else:
            print(f"  ✗ {d['symbol']:15} 無資料")

    if not prices:
        print('  ✗ 所有台股抓取失敗')
        return

    content = load()

    # 更新每支個股的收盤價和損益
    for tid, d in TW_STOCKS.items():
        p = prices.get(tid)
        if not p:
            continue
        mv  = p * d['shares']
        pnl = mv - d['ct']
        pct = pnl / d['ct'] * 100
        cc  = 'up' if pnl >= 0 else 'dn'
        s   = '+' if pnl >= 0 else ''
        chg_cc = 'up' if prices.get(tid, d['cost']) >= d['cost'] else 'dn'

        # 更新總覽表格格式（用精確的成本均價定位）
        cost_str = f'${d["cost"]}'
        pattern = (rf'(<td[^>]*>{re.escape(cost_str)}</td><td[^>]*>\$?)[\d,.]+'
                   rf'(</td><td[^>]*>)[^<]+(</td><td[^>]*>[\d,]+</td><td[^>]*>)[\d,]+'
                   rf'(</td><td[^>]*>)[^<]+(</td><td[^>]*>)[^<]+(</td>)')

        def make_row(m, price=p, mv=mv, pnl=pnl, pct=pct, cc=cc, s=s):
            return (m.group(1) + f'{price:g}' +
                    m.group(2) + f'{price:+.2f}%' +
                    m.group(3) + f'{mv:,.0f}' +
                    m.group(4) + f'{s}{abs(pnl):,.0f}' +
                    m.group(5) + f'{s}{abs(pct):.1f}%' +
                    m.group(6))

        content = re.sub(pattern, make_row, content, count=1)

    # 計算合計
    tw_mv  = sum(prices.get(t, d['cost']) * d['shares'] for t, d in TW_STOCKS.items())
    tw_ct  = sum(d['ct'] for d in TW_STOCKS.values())
    tw_pnl = tw_mv - tw_ct
    tw_pct = tw_pnl / tw_ct * 100
    s = '+' if tw_pnl >= 0 else ''

    # 更新 tfoot
    content = re.sub(
        r'(<td>2,437,850</td><td class="up">)[\d,]+(</td><td class="up">)[+\-][\d,]+(</td><td class="up">)[+\-][\d.]+%',
        f'\\g<1>{tw_mv:,.0f}\\g<2>{s}{abs(tw_pnl):,.0f}\\g<3>{s}{abs(tw_pct):.1f}%',
        content
    )

    # 更新總覽卡片
    content = re.sub(
        r'台股\d+/\d+參考市值</div><div class="tot-val up">NT\$[\d,]+</div><div class="tot-sub">[^<]+</div>',
        f'台股{mmdd}參考市值</div><div class="tot-val up">NT${tw_mv:,.0f}</div><div class="tot-sub">Yahoo Finance {date_str} 14:30</div>',
        content
    )

    # 更新表頭
    content = re.sub(
        r'🇹🇼 台股持倉一覽（\d{4}/\d{2}/\d{2} 14:30[^）]+）',
        f'🇹🇼 台股持倉一覽（{date_str} 14:30 Yahoo股市收盤 · 全部已確認）',
        content
    )
    content = re.sub(r'<th>\d+/\d+收盤</th><th>漲跌幅</th>',
                     f'<th>{mmdd}收盤</th><th>漲跌幅</th>', content, count=1)
    content = re.sub(r'持倉總覽 ｜ \d{4}/\d{2}/\d{2}[^<]+',
                     f'持倉總覽 ｜ {date_str} 台股收盤更新', content)
    content = re.sub(r'資料基準：[\d/]+（美股）/ [\d/]+（台股）',
                     f'資料基準：{-get_us_date(content)}（美股）/ {date_str}（台股）',
                     content)

    save(content)
    print(f'  ✓ 台股更新完成 NT${tw_mv:,.0f}（{s}{abs(tw_pct):.1f}%）')

# ── 美股更新 ──────────────────────────────────────────────
def run_us():
    now = tw_now()
    date_str = fmt_date(now)
    mmdd = now.strftime('%m/%d').lstrip('0').replace('/0','/')
    print(f'\n=== 美股更新 {date_str} ===')

    symbols = [d['symbol'] for d in US_STOCKS.values()]
    raw = fetch_yahoo(symbols)

    prices = {}
    for tid, d in US_STOCKS.items():
        info = raw.get(d['symbol'])
        if info and info.get('price'):
            prices[tid] = info['price']
            mv = info['price'] * d['shares']
            pnl = mv - d['ct']
            print(f"  ✓ {d['symbol']:6} ${info['price']:.2f} 損益${pnl:+,.0f}")
        else:
            print(f"  ✗ {d['symbol']:6} 無資料")

    if not prices:
        print('  ✗ 所有美股抓取失敗')
        return

    content = load()

    # 更新每支美股收盤（直接用 regex 找到該行的收盤欄位替換）
    for tid, d in US_STOCKS.items():
        p = prices.get(tid)
        if not p:
            continue
        mv  = p * d['shares']
        pnl = mv - d['ct']
        pct = pnl / d['ct'] * 100
        s   = '+' if pnl >= 0 else ''
        cc  = 'up' if pnl >= 0 else 'dn'

        # 美股表格格式：cost → close → mv → pnl → pct
        cost_str = f'${d["cost"]}'
        pattern = (rf'({re.escape(cost_str)}</td><td>\$[\d,]+</td><td class="[^"]+">)\$[\d.]+'
                   rf'(</td><td class="[^"]+">\$[\d,]+</td>\s*<td class="[^"]+">[+\-]\$[\d,]+'
                   rf'</td><td class="[^"]+">[+\-][\d.]+%)')

        replacement = (f'\\g<1>${p:.2f}'
                       f'</td><td class="{cc}">${mv:,.0f}</td>\n'
                       f'                <td class="{cc}">{s}${abs(pnl):,.0f}'
                       f'</td><td class="{cc}">{s}{abs(us_pct):.1f}%')
        content = re.sub(pattern, replacement, content, count=1)

    # 更新 tfoot
    us_mv  = sum(prices.get(t, d['cost']) * d['shares'] for t, d in US_STOCKS.items())
    us_ct  = sum(d['ct'] for d in US_STOCKS.values())
    us_pnl = us_mv - us_ct
    us_pct = us_pnl / us_ct * 100
    s = '+' if us_pnl >= 0 else ''

    content = re.sub(
        r'(美股合計（9支）</td><td>\$13,472</td><td colspan="2" class="up">\$)[\d,]+',
        f'\\g<1>{us_mv:,.0f}',
        content
    )
    content = re.sub(
        r'(<td class="up">\$)[+\-][\d,]+(</td><td class="up">)[+\-][\d.]+%</td><td></td>',
        f'\\g<1>{s}{abs(us_pnl):,.0f}\\g<2>{s}{abs(us_pct):.1f}%</td><td></td>',
        content
    )

    # 更新總覽卡片
    content = re.sub(
        r'美股\d)/\d+參考市值</div><div class="tot-val up">\$[\d,]+</div><div class="tot-sub">[^<]+</div>',
        f'美股{mmdd}參考市值</div><div class="tot-val up">${us_mv:,.0f}</div><div class="tot-sub">Yahoo Finance {date_str}</div>',
        content
    )

    # 更新美股表頭
    content = re.sub(
        r'🇺🇸 美股持倉一覽（[^）]+）',
        f'🇺🇸 美股持倉一覽（{date_str} Yahoo Finance 收盤）',
        content
    )
    content = re.sub(r'<th>\d+/\d+收盤</th><th>參考市值</th>',
                     f'<th>{mmdd}收盤</th><th>參考市值</th>', content, count=1)
    content = re.sub(r'資料基準：[\d/]+（美股）/ [\d/]+（台股）',
                     f'資料基準：{date_str}（美股）/ {_get_tw_date(content)}（台股）',
                     content)

    save(content)
    print(f'  ✓ 美股更新完成 ${us_mv:,.0f}（{s}{abs(us_pct):.1f}%）')

# ── 基金更新 ──────────────────────────────────────────────
def run_fund():
    now = tw_now()
    date_str = fmt_date(now)
    print(f'\n=== 基金淨值更新 {date_str} ===')

    content = load()
    updated = 0

    for fid, fd in FUNDS.items():
        print(f'  抓取 {fd["name"]}（{fd["moneydj"]}）...')
        result = fetch_fund_nav(fd['moneydj'])
        time.sleep(1)

        if not result:
            print(f'  ✗ {fid} 失敗，跳過')
            continue

        nav  = result['nav']
        ndate = result['date']
        mv   = nav * fd['units']
        pnl  = mv - fd['cost_usd']
        pct  = pnl / fd['cost_usd'] * 100
        s    = '+' if pct >= 0 else ''
        print(f'  ✓ {fid}: NAV={nav}（{ndate}）現值=${mv:,.2f} {s}{pct:.2f}%')

        # 更新 HOLDINGS note
        content = re.sub(
            rf"('{fid}':\s*{{[^}}]*?note:')[^']*'",
            lambda m, n=nav, nd=ndate, pc=pct, sg=s:
                m.group(1) + f'參考淨值${n}（{nd}）；現值${mv:,.2f}；損益{sg}{abs(pct):.2f}%\'',
            content, count=1
        )
        updated += 1

    save(content)
    print(f'  ✓ 基金更新完成，共 {updated}/{len(FUNDS)} 支')

def _get_tw_date(content):
    m = re.search(r'資料基準：[\d/]+（美股）/ ([\d/]+)（台股）', content)
    return m.group(1) if m else '2026/05/29'

def _get_us_date(content):
    m = re.search(r'資料基準：([\d/]+)（美股）', content)
    return m.group(1) if m else '2026/05/29'

# ── 主程式 ────────────────────────────────────────────────
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'tw'
    if not HTML_FILE.exists():
        print(f'✗ 找不到 {HTML_FILE}')
        sys.exit(1)
    {'tw': run_tw, 'us': run_us, 'fund': run_fund,
     'all': lambda: (run_tw(), run_us(), run_fund())
    }.get(mode, lambda: print('用法: python update_prices.py [tw|us|fund|all]'))()
