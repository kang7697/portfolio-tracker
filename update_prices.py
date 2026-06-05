#!/usr/bin/env python3
import re,sys,time,json,datetime,urllib.request
from pathlib import Path

TW={'t631':{'symbol':'00631L.TW','shares':2000,'ct':59860},
    't922':{'symbol':'00922.TW','shares':11000,'ct':319330},
    't882':{'symbol':'00882.TW','shares':28000,'ct':355040},
    't955':{'symbol':'00955.TWO','shares':20000,'ct':311400},
    't9816':{'symbol':'009816.TW','shares':6000,'ct':61500},
    't990':{'symbol':'00990A.TW','shares':7000,'ct':82880},
    't2313':{'symbol':'2313.TW','shares':1000,'ct':222820},
    't2359':{'symbol':'2359.TW','shares':2000,'ct':248860},
    't3481':{'symbol':'3481.TW','shares':3000,'ct':76170},
    't8070':{'symbol':'8070.TWO','shares':1000,'ct':43060},
    't6488':{'symbol':'6488.TWO','shares':0,'ct':0}}
US={'ag':{'symbol':'AG','shares':110,'ct':2212},
    'be':{'symbol':'BE','shares':2,'ct':550},
    'cohr':{'symbol':'COHR','shares':6,'ct':1414},
    'tsm':{'symbol':'TSM','shares':6,'ct':1983},
    'tsla':{'symbol':'TSLA','shares':5,'ct':1938},
    'uuuu':{'symbol':'UUUU','shares':121,'ct':2524},
    'eose':{'symbol':'EOSE','shares':40,'ct':313},
    'nbis':{'symbol':'NBIS','shares':3,'ct':261},
    'onds':{'symbol':'ONDS','shares':20,'ct':179},
    'orcl':{'symbol':'ORCL','shares':4,'ct':645}}
FUNDS={'f1':'tlzm8','f2':'pim91','f3':'pim90','f4':'tlh43','f5':'wea84'}
HTML=Path('portfolio_tracker_v3.html')

def now_tw():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

def yahoo(syms):
    url=f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={",".join(syms)}&fields=regularMarketPrice,regularMarketChangePercent'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=15) as r: data=json.loads(r.read())
        return {q['symbol']:{'p':q.get('regularMarketPrice'),'c':q.get('regularMarketChangePercent',0)}
                for q in data.get('quoteResponse',{}).get('result',[])}
    except Exception as e: print(f'Yahoo:{e}'); return {}

def nav(code):
    url=f'https://www.moneydj.com/funddj/ya/yp010001.djhtm?a={code}'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.moneydj.com/'})
        with urllib.request.urlopen(req,timeout=20) as r: t=r.read().decode('utf-8','replace')
        m=re.search(r'\d{4}/\d{2}/\d{2}[^<]*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>',t)
        if m: return float(m.group(1))
    except Exception as e: print(f'Nav:{e}')
    return None

def upd(h,pid,pv,pc,dl):
    idx=h.find(f'id="p-{pid}"')
    if idx<0: return h
    nxt=h.find('\n<div id="p-',idx+10); b=nxt if nxt>0 else idx+5000
    s=h[idx:b]
    ar='▲' if pc>=0 else '▼'; cc='up' if pc>=0 else 'dn'; sg='+' if pc>=0 else ''
    ps=f'${pv}'
    s=re.sub(r'class="pch-price [^"]*">[^<]+<span[^>]*>[^<]*</span></div>',
             f'class="pch-price {cc}">{ps} <span style="font-size:13px">{ar}{sg}{abs(pc):.2f}%</span></div>',s,1)
    s=re.sub(r'(<div style="font-size:11px[^>]*>)\d+/\d+[^<]*(收盤|淨值|追蹤)[^|<]*',
             f'\g<1>{dl}收盤 ',s,1)
    s=re.sub(r'(<div class="pnl-label">)\d+/\d+(收盤</div>)',f'\g<1>{dl}收盤</div>',s,1)
    s=re.sub(r'(class="pnl-label">\d+/\d+收盤</div>\s*<div class="pnl-val )[^"]*(">)\$[\d.]+',
             f'\g<1>{cc}\g<2>{ps}',s,1)
    return h[:idx]+s+h[b:]

def run_tw():
    t=now_tw(); ds=t.strftime('%Y/%m/%d'); dl=f'{t.month}/{t.day}'
    print(f'=== TW {ds} ==='); raw=yahoo([d['symbol'] for d in TW.values()])
    h=HTML.read_text('utf-8')
    for tid,d in TW.items():
        info=raw.get(d['symbol'])
        if not info or not info.get('p'): continue
        h=upd(h,tid,info['p'],info['c'],dl); print(f"  {d['symbol']}:${info['p']}")
    for pat,rep in [
        (r'台股[\d/]+參考市值',f'台股{dl}參考市值'),
        (r'Yahoo股市 [\d/]+ 14:30',f'Yahoo股市 {dl} 14:30'),
        (r'台股持倉一覽（[^）]+）',f'台股持倉一覽（{ds} 14:30 Yahoo股市收盤 · 全部已確認）'),
        (r'<th>\d+/\d+收盤</th><th>漲跌幅</th>',f'<th>{dl}收盤</th><th>漲跌幅</th>'),
        (r'持倉總覽 ｜ [\d/]+[^<]*',f'持倉總覽 ｜ {ds} 台股收盤更新'),
        (r'資料基準：([\d/]+)（美股[^）]*）/ [\d/]+（台股）',f'\g<1>（美股）/ {ds}（台股）')]:
        h=re.sub(pat,rep,h)
    HTML.write_text(h,'utf-8'); print('TW done')

def run_us():
    t=now_tw(); ds=t.strftime('%Y/%m/%d'); dl=f'{t.month}/{t.day}'
    print(f'=== US {ds} ==='); raw=yahoo([d['symbol'] for d in US.values()])
    h=HTML.read_text('utf-8')
    for tid,d in US.items():
        info=raw.get(d['symbol'])
        if not info or not info.get('p'): continue
        h=upd(h,tid,info['p'],info['c'],dl); print(f"  {d['symbol']}:${info['p']}")
    for pat,rep in [
        (r'美股[\d/]+參考市值',f'美股{dl}參考市值'),
        (r'美股持倉一覽（[^）]+）',f'美股持倉一覽（{ds} Yahoo股市昨收確認）'),
        (r'<th>\d+/\d+收盤</th><th>參考市值</th>',f'<th>{dl}收盤</th><th>參考市值</th>'),
        (r'資料基準：[\d/]+（美股[^）]*）/ ([\d/]+（台股）)',f'{ds}（美股）/ \g<1>')]:
        h=re.sub(pat,rep,h)
    HTML.write_text(h,'utf-8'); print('US done')

def run_fund():
    t=now_tw(); dl=f'{t.month}/{t.day}'
    print('=== FUND ==='); h=HTML.read_text('utf-8')
    for fid,code in FUNDS.items():
        nv=nav(code); time.sleep(1)
        if not nv: continue
        idx=h.find(f'id="p-{fid}"')
        if idx<0: continue
        nxt=h.find('\n<div id="p-',idx+10); b=nxt if nxt>0 else idx+3000
        s=h[idx:b]; pct=(nv-1)*100  # 簡化
        cc='up' if nv>0 else 'dn'; ar='▲'
        s=re.sub(r'class="pch-price [^"]*">USD [\d.]+[^<]*<span[^>]*>[^<]*</span></div>',
                 f'class="pch-price {cc}">USD {nv} <span style="font-size:13px">{ar}</span></div>',s,1)
        s=re.sub(r'(<div style="font-size:11px[^>]*>)\d+/\d+[^<]*(淨值)[^<]*',
                 f'\g<1>{dl}淨值 MoneyDJ',s,1)
        h=h[:idx]+s+h[b:]; print(f'  {fid}:NAV={nv}')
    HTML.write_text(h,'utf-8'); print('FUND done')

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'all'
    if not HTML.exists(): sys.exit(f'no {HTML}')
    if mode=='tw': run_tw()
    elif mode=='us': run_us()
    elif mode=='fund': run_fund()
    else: run_tw(); run_us(); run_fund()