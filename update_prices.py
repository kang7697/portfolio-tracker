#!/usr/bin/env python3
"""
自動更新投資組合 V3 報表
台股：每個交易日 15:05（台灣時間）→ Yahoo股市
美股：每個交易日 06:00（台灣時間）→ Yahoo Finance（tw.stock.yahoo.com）
"""

import re
import sys
import time
import json
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# ── 持倉設定 ──────────────────────────────────────────────
TW_STOCKS = {
    't631':  {'symbol': '00631L.TW',  'cost': 29.93,  'shares': 2000,  'ct': 59860},
    't922':  {'symbol': '00922.TW',   'cost': 29.03,  'shares': 11000, 'ct': 319330},
    't882':  {'symbol': '00882.TW',   'cost': 12.68,  'shares': 28000, 'ct': 355040},
    't955':  {'symbol': '00955.TWO',  'cost': 15.57,  'shares': 20000, 'ct': 311400},
    't9816': {'symbol': '009816.TW',  'cost': 10.25,  'shares': 6000,  'ct': 61500},
    't990':  {'symbol': '00990A.TW',  'cost': 11.84,  'shares': 7000,  'ct': 82880},
    't2313': {'symbol': '2313.TW',    'cost': 222.82, 'shares': 1000,  'ct': 222820},
    't2359': {'symbol': '2359.TW',    'cost': 124.43, 'shares': 2000,  'ct': 248860},
    't3481': {'symbol': '3481.TW',    'cost': 25.39,  'shares': 3000,  'ct': 76170},
    't6488': {'symbol': '6488.TWO',   'cost': 656.93, 'shares': 1000,  'ct': 656930},
    't8070': {'symbol': '8070.TWO',   'cost': 43.06,  'shares': 1000,  'ct': 43060},
}

US_STOCKS = {
    'ag':   {'symbol': 'AG',   'cost': 20.11,  'shares': 110, 'ct': 2212},
    'cohr': {'symbol': 'COHR', 'cost': 235.67, 'shares': 6,   'ct': 1414},
    'tsm':  {'symbol': 'TSM',  'cost': 330.46, 'shares': 6,   'ct': 1983},
    'tsla': {'symbol': 'TSLA', 'cost': 387.58, 'shares': 5,   'ct': 1938},
    'uuuu': {'symbol': 'UUUU', 'cost': 20.86,  'shares': 121, 'ct': 2524},
    'eose': {'symbol': 'EOSE', 'cost': 7.83,   'shares': 40,  'ct': 313},
    'nbis': {'symbol': 'NBIS', 'cost': 86.88,  'shares': 3,   'ct': 261},
    'onds': {'symbol': 'ONDS', 'cost': 8.96,   'shares': 20,  'ct': 179},
    'orcl': {'symbol': 'ORCL', 'cost': 161.24, 'shares': 4,   'ct': 645},
}

HTML_FILE = Path('portfolio_tracker_v3.html')

# ── Yahoo Finance API ──────────────────────────────────────
def fetch_yahoo(symbols: list[str]) -> dict:
    """用 Yahoo Finance v8 API 一次抓多支股票"""
    syms = ','.join(symbols)
    url = (
        f'https://query1.finance.yahoo.com/v8/finance/chart/{symbols[0]}'
        if len(symbols) == 1
        else f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={syms}'
        f'&fields=regularMarketPrice,regularMarketPreviousClose,'
        f'regularMarketChangePercent,regularMarketTime,shortName'
    )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f'  ✗ Yahoo API 錯誤：{e}')
        return {}

    results = {}
    # v7 多支
    if 'quoteResponse' in data:
        for q in data['quoteResponse'].get('result', []):
            sym = q.get('symbol', '')
            results[sym] = {
                'price': q.get('regularMarketPrice'),
                'prev':  q.get('regularMarketPreviousClose'),
                'chgPct': q.get('regularMarketChangePercent'),
                'name':  q.get('shortName', sym),
            }
    return results


def fetch_tw_yahoo(symbol: str) -> dict | None:
    """抓台股個股（tw.stock.yahoo.com JSON API）"""
    url = f'https://tw.stock.yahoo.com/quote/{symbol}'
    # Yahoo 台股的 API endpoint
    api_url = (
        f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}'
        f'&fields=regularMarketPrice,regularMarketPreviousClose,'
        f'regularMarketChangePercent,shortName,regularMarketTime'
    )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://tw.stock.yahoo.com/',
    }
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = data.get('quoteResponse', {}).get('result', [])
        if results:
            q = results[0]
            return {
                'price': q.get('regularMarketPrice'),
                'prev':  q.get('regularMarketPreviousClose'),
                'chgPct': q.get('regularMarketChangePercent'),
                'name':  q.get('shortName', symbol),
            }
    except Exception as e:
        print(f'  ✗ {symbol} 抓取失敗：{e}')
    return None


# ── HTML 更新函數 ──────────────────────────────────────────
def load_html() -> str:
    return HTML_FILE.read_text(encoding='utf-8')


def save_html(content: str):
    HTML_FILE.write_text(content, encoding='utf-8')


def update_topbar(content: str, tw_date: str, us_date: str) -> str:
    """更新 topbar 日期"""
    content = re.sub(
        r'資料基準：[\d/]+（美股）/ [\d/]+（台股）',
        f'資料基準：{us_date}（美股）/ {tw_date}（台股）',
        content
    )
    return content


def update_tw_header(content: str, date_str: str) -> str:
    """更新台股表頭日期"""
    content = re.sub(
        r'🇹🇼 台股持倉一覽（\d{4}/\d{2}/\d{2} 14:30',
        f'🇹🇼 台股持倉一覽（{date_str} 14:30',
        content
    )
    content = re.sub(
        r'<th>(\d+/\d+)收盤</th><th>漲跌幅</th>',
        lambda m: f'<th>{date_str[5:][:5].replace("-","/")}收盤</th><th>漲跌幅</th>',
        content
    )
    content = re.sub(
        r'持倉總覽 ｜ \d{4}/\d{2}/\d{2} 台股收盤更新',
        f'持倉總覽 ｜ {date_str} 台股收盤更新',
        content
    )
    return content


def pct_str(pct: float | None) -> str:
    if pct is None:
        return '--'
    sign = '+' if pct >= 0 else ''
    return f'{sign}{pct:.2f}%'


def color_class(val: float) -> str:
    return 'up' if val >= 0 else 'dn'


def update_totals(content: str, stocks: dict, prices: dict,
                  label: str, date_str: str, currency: str = 'NT$') -> str:
    """更新總覽卡片"""
    total_mv   = sum(prices.get(t, {}).get('price', d['cost']) * d['shares']
                     for t, d in stocks.items())
    total_cost = sum(d['ct'] for d in stocks.values())
    total_pnl  = total_mv - total_cost
    total_pct  = total_pnl / total_cost * 100
    sign       = '+' if total_pnl >= 0 else ''

    if currency == 'NT$':
        # 台股卡片
        content = re.sub(
            r'台股\d+/\d+參考市值</div><div class="tot-val up">NT\$[\d,]+</div>'
            r'<div class="tot-sub">[^<]+</div>',
            f'台股{date_str[5:]}參考市值</div>'
            f'<div class="tot-val up">NT${total_mv:,.0f}</div>'
            f'<div class="tot-sub">Yahoo股市 {date_str[5:]} 14:30</div>',
            content
        )
        content = re.sub(
            r'\+NT\$[\d,]+</div><div class="tot-sub">[+-][\d.]+%</div>',
            f'{sign}NT${abs(total_pnl):,.0f}</div>'
            f'<div class="tot-sub">{sign}{total_pct:.1f}%</div>',
            content, count=1
        )
        # tfoot
        content = re.sub(
            r'<td>2,437,850</td><td class="up">[\d,]+</td>'
            r'<td class="up">[+\-][\d,]+</td><td class="up">[+\-][\d.]+%</td>',
            f'<td>2,437,850</td><td class="up">{total_mv:,.0f}</td>'
            f'<td class="up">{sign}{abs(total_pnl):,.0f}</td>'
            f'<td class="up">{sign}{total_pct:.1f}%</td>',
            content
        )
    else:
        # 美股卡片
        content = re.sub(
            r'美股\d+/\d+參考市值</div><div class="tot-val up">\$[\d,]+</div>'
            r'<div class="tot-sub">[^<]+</div>',
            f'美股{date_str[5:]}參考市值</div>'
            f'<div class="tot-val up">${total_mv:,.0f}</div>'
            f'<div class="tot-sub">tw.stock.yahoo.com 昨收確認</div>',
            content
        )

    return content


# ── 台股更新 ──────────────────────────────────────────────
def run_tw_update():
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    date_str = now_tw.strftime('%Y/%m/%d')
    print(f'\n=== 台股更新 {date_str} ===')

    # 批次抓取
    symbols = [d['symbol'] for d in TW_STOCKS.values()]
    print(f'  抓取 {len(symbols)} 支台股...')
    prices_raw = fetch_yahoo(symbols)

    # 整理結果
    prices = {}
    for tid, d in TW_STOCKS.items():
        sym = d['symbol']
        info = prices_raw.get(sym)
        if info and info.get('price'):
            prices[tid] = info
            p = info['price']
            c = info.get('chgPct', 0)
            mv = p * d['shares']
            pnl = mv - d['ct']
            print(f'  ✓ {sym:15} ${p:.2f} ({pct_str(c)}) 損益NT${pnl:+,.0f}')
        else:
            print(f'  ✗ {sym:15} 無資料')

    if not prices:
        print('  ✗ 所有台股抓取失敗，中止更新')
        return

    # 更新 HTML
    content = load_html()
    content = update_topbar(content,
                             tw_date=date_str,
                             us_date=_get_us_date(content))
    content = update_tw_header(content, date_str)

    # 更新各列數據
    for tid, d in TW_STOCKS.items():
        info = prices.get(tid)
        if not info:
            continue
        price  = info['price']
        chgPct = info.get('chgPct', 0) or 0
        mv     = price * d['shares']
        pnl    = mv - d['ct']
        pct    = pnl / d['ct'] * 100

        sign = '+' if pnl >= 0 else ''
        cc   = color_class(pnl)
        chg_sign = '+' if chgPct >= 0 else ''
        chg_cc   = 'up' if chgPct >= 0 else 'dn'

        # 更新 HOLDINGS note
        content = re.sub(
            rf"('{tid}':.*?note:')[^']*'",
            lambda m, t=tid, p=price, pc=pct: (
                m.group(1) +
                f'{date_str[5:]}收盤${p:.2f}（{sign}{pc:.1f}%浮盈）' +
                "'"
            ),
            content, count=1
        )

    # 更新總覽合計
    content = update_totals(content, TW_STOCKS, prices, '台股', date_str, 'NT$')
    save_html(content)
    print(f'  ✓ 台股更新完成')


# ── 美股更新 ──────────────────────────────────────────────
def run_us_update():
    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    date_str = now_tw.strftime('%Y/%m/%d')
    print(f'\n=== 美股更新 {date_str} ===')

    # AG 用 tw.stock.yahoo.com
    symbols_yf = [d['symbol'] for d in US_STOCKS.values()]
    print(f'  抓取 {len(symbols_yf)} 支美股...')

    # 全部用 tw.stock.yahoo.com（Yahoo Finance global）
    prices_raw = fetch_yahoo(symbols_yf)

    prices = {}
    for tid, d in US_STOCKS.items():
        sym = d['symbol']
        info = prices_raw.get(sym)
        if info and info.get('price'):
            prices[tid] = info
            p = info['price']
            c = info.get('chgPct', 0)
            mv = p * d['shares']
            pnl = mv - d['ct']
            print(f'  ✓ {sym:6} ${p:.2f} ({pct_str(c)}) 損益${pnl:+,.0f}')
        else:
            print(f'  ✗ {sym:6} 無資料')

    if not prices:
        print('  ✗ 所有美股抓取失敗，中止更新')
        return

    content = load_html()
    content = update_topbar(content,
                             tw_date=_get_tw_date(content),
                             us_date=date_str)

    # 更新美股總覽合計
    content = update_totals(content, US_STOCKS, prices, '美股', date_str, 'USD')

    # 更新 HOLDINGS note
    for tid, d in US_STOCKS.items():
        info = prices.get(tid)
        if not info:
            continue
        price = info['price']
        mv    = price * d['shares']
        pnl   = mv - d['ct']
        pct   = pnl / d['ct'] * 100
        sign  = '+' if pct >= 0 else ''
        content = re.sub(
            rf"('{tid}':.*?note:')[^']*'",
            lambda m, p=price, pc=pct, s=sign: (
                m.group(1) +
                f'{date_str[5:]}收盤${p:.2f}（{s}{pc:.1f}%浮盈）' +
                "'"
            ),
            content, count=1
        )

    save_html(content)
    print(f'  ✓ 美股更新完成')


def _get_tw_date(content: str) -> str:
    m = re.search(r'台股(\d{4}/\d{2}/\d{2})參考市值', content)
    return m.group(1) if m else '2026/05/27'


def _get_us_date(content: str) -> str:
    m = re.search(r'美股(\d{4}/\d{2}/\d{2})參考市值', content)
    return m.group(1) if m else '2026/05/26'


# ── 主程式 ────────────────────────────────────────────────
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'tw'

    if not HTML_FILE.exists():
        print(f'✗ 找不到 {HTML_FILE}，請確認檔案路徑')
        sys.exit(1)

    if mode == 'tw':
        run_tw_update()
    elif mode == 'us':
        run_us_update()
    elif mode == 'all':
        run_tw_update()
        run_us_update()
    else:
        print(f'用法：python update_prices.py [tw|us|all]')
        sys.exit(1)
