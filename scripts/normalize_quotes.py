"""Normalize daily quote snapshots with strict date and numeric checks.
This stage does not declare four-digit codes to be ordinary shares.
"""
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

ENDPOINTS = {
 "TWSE": ("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
          {"code":"Code","name":"Name","date":"Date","close":"ClosingPrice","value":"TradeValue","change":"Change"}),
 "TPEX": ("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
          {"code":"SecuritiesCompanyCode","name":"CompanyName","date":"Date","close":"Close","value":"TransactionAmount","change":"Change"})
}

def rocdate(value):
    s=str(value).strip().replace("/","").replace("-","")
    if not re.fullmatch(r"\d{7}",s): raise ValueError("invalid ROC date "+s)
    return dt.date(int(s[:3])+1911,int(s[3:5]),int(s[5:7])).isoformat()

def number(v):
    s=str(v).replace(",","").strip()
    if s in ("","--","---","-","N/A"): return None
    try: return float(s)
    except ValueError: return None

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=45) as r: return json.load(r)

def main():
    report={"generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"markets":{},"status":"NOT_VALIDATED"}
    rows=[]
    for market,(url,fields) in ENDPOINTS.items():
        data=fetch(url)
        if not isinstance(data,list) or not data: raise ValueError(market+" empty or invalid")
        dates={rocdate(x[fields["date"]]) for x in data}
        if len(dates)!=1: raise ValueError(market+" mixed dates "+str(dates))
        date=next(iter(dates))
        selected=[]
        for x in data:
            code=str(x.get(fields["code"],"")).strip()
            if not re.fullmatch(r"\d{4}",code): continue
            selected.append({"market":market,"date":date,"code":code,"name":str(x.get(fields["name"],"")).strip(),
                             "close":number(x.get(fields["close"])),"trade_value":number(x.get(fields["value"])),
                             "change":str(x.get(fields["change"],"")).strip()})
        report["markets"][market]={"date":date,"raw_rows":len(data),"four_digit_rows":len(selected),
                                   "distinct_four_digit_codes":len({x["code"] for x in selected}),
                                   "missing_close":sum(x["close"] is None for x in selected),
                                   "missing_trade_value":sum(x["trade_value"] is None for x in selected)}
        rows.extend(selected)
        print(market,report["markets"][market],flush=True)
    market_dates={v["date"] for v in report["markets"].values()}
    report["status"]="DATE_MATCH" if len(market_dates)==1 else "DATE_MISMATCH"
    report["note"]="Four-digit candidate codes not yet verified against ordinary-share master. No trading signals."
    out=Path("results");out.mkdir(exist_ok=True)
    (out/"normalized_quote_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"four_digit_quote_candidates.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    print("RESULT",report["status"],flush=True)
    if report["status"]!="DATE_MATCH": raise SystemExit("Market date mismatch; no combined stock signals")

if __name__=="__main__":main()
