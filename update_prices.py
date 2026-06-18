#!/usr/bin/env python3
import re, sys, time, datetime
from pathlib import Path
import yfinance as yf

TW = {
    't631':{'symbol':'00631L.TW','shares':2000,'ct':59860},
    't922':{'symbol':'00922.TW','shares':11000,'ct':319330},
    't882':{'symbol':'00882.TW','shares':28000,'ct':355040},
    't955':{'symbol':'00955.TWO','shares':20000,'ct':311400},
    't9816':{'symbol':'009816.TW','shares':6000,'ct':61500},
    't990':{'symbol':'00990A.TW','shares':7000,'ct':82880},
    't2313':{'symbol':'2313.TW','shares':1000,'ct':222820},
    't2359':{'symbol':'2359.TW','shares':2000,'ct':248860},
    't3481':{'symbol':'3481.TW','shares':3000,'ct':76170},
    't8070':{'symbol':'8070.TWO','shares':1000,'ct':43060},
    't6488':{'symbol':'6488.TWO','shares':0,'ct':0},
    't1802':{'symbol':'1802.TW','shares':4000,'ct':259960},
}
US = {
    'ag':{'symbol':'AG','shares':110,'ct':2212},
    'be':{'symbol':'BE','shares':2,'ct':550},
    'cohr':{'symbol':'COHR','shares':6,'ct':1414},
    'tsm':{'symbol':'TSM','shares':6,'ct':1983},
    'tsla':{'symbol':'TSLA','shares':5,'ct':1938},
    'uuuu':{'symbol':'UUUU','shares':121,'ct':2524},
    'eose':{'symbol':'EOSE','shares':40,'ct':313},
    'nbis':{'symbol':'NBIS','shares':3,'ct':261},
    'onds':{'symbol':'ONDS','shares':20,'ct':179},
    'orcl':{'symbol':'ORCL','shares':4,'ct':645},
}
FUNDS = {'f1':'tlzm8','f2':'pim91','f3':'pim90','f4':'tlh43','f5':'wea84'}
HTML = Path('portfolio_tracker_v3.html')

def now_tw():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

def fetch_prices(symbols):
    results = {}
    try:
        data = yf.download(' '.join(symbols), period='5d', interval='1d', progress=False, auto_adjust=True)
        closes = data['Close'] if hasattr(data.columns, 'levels') else data[['Close']].rename(columns={'Close': symbols[0]})
        for sym in symbols:
            try:
                vals = closes[sym].dropna()
                if len(vals) >= 2:
                    p = round(float(vals.iloc[-1]), 2)
                    prev = round(float(vals.iloc[-2]), 2)
                    results[sym] = {'p': p, 'c': round((p - prev) / prev * 100, 2)}
                    print(f'  {sym}: ${p} ({results[sym]["c"]:+.2f}%)')
            except Exception as e:
                print(f'  {sym}: {e}')
    except Exception as e:
        print(f'fetch error: {e}')
    return results

def fetch_nav(code):
    import urllib.request
    try:
        req = urllib.request.Request(
            f'https://www.moneydj.com/funddj/ya/yp010001.djhtm?a={code}',
            headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.moneydj.com/'})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode('utf-8','replace')
        m = re.search(r'\d{4}/\d{2}/\d{2}[^<]*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>', html)
        if m: return float(m.group(1))
    except Exception as e:
        print(f'MoneyDJ {code}: {e}')
    return None

def upd(h, pid, price, pct, dl, avg_cost=0, shares=0):
    """更新個股分頁：收盤card + 浮動損益card + table row"""
    idx = h.find(f'id="p-{pid}"')
    if idx < 0: return h
    nxt = h.find('\n<div id="p-', idx + 10)
    b = nxt if nxt > 0 else idx + 5000
    s = h[idx:b]
    ar = '\u25b2' if pct >= 0 else '\u25bc'
    cc = 'up' if pct >= 0 else 'dn'
    sg = '+' if pct >= 0 else ''
    ps = f'${price}'
    pct_str = f'{ar}{sg}{abs(pct):.2f}%'
    # 1. pch-price
    s = re.sub(
        r'class="pch-price [^"]*">[^<]+<span[^>]*>[^<]*</span></div>',
        f'class="pch-price {cc}">{ps} <span style="font-size:13px">{pct_str}</span></div>',
        s, 1)
    # 2. pch-subtitle
    s = re.sub(
        r'(<div style="font-size:11px[^>]*>)\d+/\d+[^<]*(\u6536[\u76d8\u76e4]|\u51c8\u5024|\u8ffd\u8e64)[^|<]*',
        rf'\g<1>{dl}\u6536\u76e4 ', s, 1)
    # 3. 收盤 pnl-card
    bg = 'up-bg' if pct >= 0 else 'dn-bg'
    new_card = ('<div class="pnl-card ' + bg + '">'
             + '<div class="pnl-label">' + dl + '\u6536\u76e4</div>'
             + '<div class="pnl-val ' + cc + '">' + ps + '</div>'
             + '<div class="pnl-sub">Yahoo\u80a1\u5e02\u6628\u6536\u78ba\u8a8d</div></div>')
    s = re.sub(
        r'<div class="pnl-card[^"]*"><div class="pnl-label">\d+/\d+[^<]*\u6536[\u76d8\u76e4][^<]*</div>[\s\S]*?</div>\s*</div>',
        new_card, s, 1)
    # 4. 浮動損益 pnl-card
    if avg_cost > 0 and shares > 0:
        pnl_val = round((price - avg_cost) * shares)
        pnl_pct = round((price - avg_cost) / avg_cost * 100, 2)
        pnl_cc = 'up' if pnl_val >= 0 else 'dn'
        pnl_bg = 'up-bg' if pnl_val >= 0 else 'dn-bg'
        pnl_sg = '+' if pnl_val >= 0 else ''
        pnl_card = ('<div class="pnl-card ' + pnl_bg + '">'
                  + '<div class="pnl-label">\u6d6e\u52d5\u640d\u76ca</div>'
                  + '<div class="pnl-val ' + pnl_cc + '">' + pnl_sg + '$' + f'{abs(pnl_val):,}' + '</div>'
                  + '<div class="pnl-sub">' + pnl_sg + f'{abs(pnl_pct):.2f}' + '%</div></div>')
        s = re.sub(
            r'<div class="pnl-card[^"]*"><div class="pnl-label">\u6d6e\u52d5\u640d\u76ca</div>[\s\S]*?</div>\s*</div>',
            pnl_card, s, 1)
    h = h[:idx] + s + h[b:]
    # 5. table row 更新
    if avg_cost > 0 and shares > 0:
        pnl_val = round((price - avg_cost) * shares)
        pnl_pct = round((price - avg_cost) / avg_cost * 100, 2)
        pnl_sg = '+' if pnl_val >= 0 else ''
        pct_sg = '+' if pct >= 0 else ''
        mv = round(price * shares)
        cl_cc = 'up' if pct >= 0 else 'dn'
        pnl_cc2 = 'up' if pnl_val >= 0 else 'dn'
        row_s = h.find(f'id="row-{pid}"')
        if row_s >= 0:
            row_e = h.find('</tr>', row_s) + 5
            row = h[row_s:row_e]
            row = re.sub(rf'<td class="[^"]*" id="cl-{pid}">[^<]*</td>',
                         f'<td class="{cl_cc}" id="cl-{pid}">${price}</td>', row)
            row = re.sub(rf'(<td class="[^"]*" id="cl-{pid}">[^<]*</td>)<td[^>]*>[^<]*</td>',
                         rf'\g<1><td class="{cl_cc}">{pct_sg}{abs(pct):.2f}%</td>', row, 1)
            row = re.sub(r'(<td[^>]*>[+\-]?[\d.]+%</td>)<td>\$[\d,]+</td>',
                         rf'\g<1><td>${mv:,}</td>', row, 1)
            row = re.sub(rf'<td class="[^"]*" id="pnl-{pid}">[^<]*</td>',
                         f'<td class="{pnl_cc2}" id="pnl-{pid}">{pnl_sg}${abs(pnl_val):,}</td>', row)
            row = re.sub(rf'<td class="[^"]*" id="pp-{pid}">[^<]*</td>',
                         f'<td class="{pnl_cc2}" id="pp-{pid}">{pnl_sg}{abs(pnl_pct):.2f}%</td>', row)
            h = h[:row_s] + row + h[row_e:]
    return h
def run_tw():
    t = now_tw(); ds = t.strftime('%Y/%m/%d'); dl = f'{t.month}/{t.day}'
    print(f'=== TW {ds} ===')
    raw = fetch_prices([d['symbol'] for d in TW.values()])
    h = HTML.read_text('utf-8')
    for tid, d in TW.items():
        info = raw.get(d['symbol'])
        if not info: continue
        h = upd(h, tid, info['p'], info['c'], dl, round(d['ct']/d['shares'],2) if d['shares']>0 else 0, d['shares'])
    h = re.sub(r'台股[\d/]+參考市值', f'台股{dl}參考市值', h)
    h = re.sub(r'Yahoo股市 [\d/]+ 14:30', f'Yahoo股市 {dl} 14:30', h)
    h = re.sub(r'台股持倉一覽（[^）]+）', f'台股持倉一覽（{ds} 14:30 Yahoo股市收盤）', h)
    h = re.sub(r'<th>\d+/\d+收盤</th><th>漲跌幅', f'<th>{dl}收盤</th><th>漲跌幅', h)
    h = re.sub(r'持倉總覽 ｜ [^<]*', f'持倉總覽 ｜ {ds} 台股收盤更新', h)
    HTML.write_text(h, 'utf-8'); print('TW done')

def run_us():
    t = now_tw(); ds = t.strftime('%Y/%m/%d'); dl = f'{t.month}/{t.day}'
    print(f'=== US {ds} ===')
    raw = fetch_prices([d['symbol'] for d in US.values()])
    h = HTML.read_text('utf-8')
    for tid, d in US.items():
        info = raw.get(d['symbol'])
        if not info: continue
        h = upd(h, tid, info['p'], info['c'], dl, round(d['ct']/d['shares'],2) if d['shares']>0 else 0, d['shares'])
    h = re.sub(r'美股[\d/]+參考市值', f'美股{dl}參考市值', h)
    h = re.sub(r'美股持倉一覽（[^）]+）', f'美股持倉一覽（{ds} Yahoo股市昨收確認）', h)
    h = re.sub(r'<th>\d+/\d+收[盤盘]</th><th>參考市值', f'<th>{dl}收盤</th><th>參考市值', h)
    h = re.sub(r'資料基準：[\d/]+（美股[^）]*）', f'資料基準：{ds}（美股）', h)
    h = re.sub(r'美股[\d/]+參考市值', f'美股{dl}參考市值', h)
    HTML.write_text(h, 'utf-8'); print('US done')

def run_fund():
    t = now_tw(); dl = f'{t.month}/{t.day}'
    print('=== FUND ===')
    h = HTML.read_text('utf-8')
    for fid, code in FUNDS.items():
        nav = fetch_nav(code); time.sleep(1)
        if not nav: continue
        idx = h.find(f'id="p-{fid}"')
        if idx < 0: continue
        nxt = h.find('\n<div id="p-', idx + 10); b = nxt if nxt > 0 else idx + 3000
        s = h[idx:b]
        s = re.sub(
            r'class="pch-price [^"]*">USD [\d.]+[^<]*<span[^>]*>[^<]*</span></div>',
            f'class="pch-price up">USD {nav} <span style="font-size:13px">▲</span></div>', s, 1)
        s = re.sub(
            r'(<div style="font-size:11px[^>]*>)\d+/\d+[^<]*(淨值)[^<]*',
            rf'\g<1>{dl}淨值 MoneyDJ', s, 1)
        h = h[:idx] + s + h[b:]
        print(f'  {fid}: NAV={nav}')
    HTML.write_text(h, 'utf-8'); print('FUND done')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if not HTML.exists(): sys.exit(f'no {HTML}')
    if mode == 'tw': run_tw()
    elif mode == 'us': run_us()
    elif mode == 'fund': run_fund()
    else: run_tw(); run_us(); run_fund()