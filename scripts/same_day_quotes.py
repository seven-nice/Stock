"""Stage 5: retrieve both official markets for the same explicitly requested day.
This is an audit snapshot, NOT a verified ordinary-share universe or signal.
"""
import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

def fetch(url):
    request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=60) as r:
        return json.load(r)

def parse_number(value):
    s=str(value).strip().replace(",","")
    if s in ("","--","---","-","N/A","None"): return None
    try: return float(s)
    except ValueError: return None

def main():
    target=sys.argv[1] if len(sys.argv)>1 else (dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()-dt.timedelta(days=1)).isoformat()
    day=dt.date.fromisoformat(target)
    compact=day.strftime("%Y%m%d")
    twse_url="https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?"+urllib.parse.urlencode({"response":"json","date":compact,"type":"ALLBUT0999"})
    tpex_url="https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?"+urllib.parse.urlencode({"response":"json","date":day.strftime("%Y/%m/%d"),"type":"EW"})
    report={"target_date":target,"sources":{},"status":"INCOMPLETE","ordinary_share_verified":False}
    records=[]
    try:
        twse=fetch(twse_url)
        if twse.get("stat")!="OK" or str(twse.get("date"))!=compact: raise ValueError("TWSE status/date mismatch")
        tables=twse.get("tables",[])
        table=next(t for t in tables if "每日收盤行情" in str(t.get("title","")) and "證券代號" in t.get("fields",[]))
        fields=table["fields"]
        def ix(k): return fields.index(k)
        for raw in table.get("data",[]):
            code=str(raw[ix("證券代號")]).strip()
            if re.fullmatch(r"\d{4}",code):
                records.append({"market":"TWSE","date":target,"code":code,"name":str(raw[ix("證券名稱")]).strip(),
                                "close":parse_number(raw[ix("收盤價")]),"trade_value_twd":parse_number(raw[ix("成交金額")]),
                                "change_sign":str(raw[ix("漲跌(+/-)")]).strip(),
                                "change_amount":parse_number(raw[ix("漲跌價差")])})
        report["sources"]["TWSE"]={"date":target,"raw_rows":len(table.get("data",[])),
            "four_digit_rows":sum(r["market"]=="TWSE" for r in records),"url":twse_url}
    except Exception as e: report["sources"]["TWSE"]={"error":f"{type(e).__name__}: {e}"}
    try:
        tpex=fetch(tpex_url)
        if str(tpex.get("stat","")).lower()!="ok" or str(tpex.get("date"))!=compact: raise ValueError("TPEx status/date mismatch")
        tables=tpex.get("tables",[])
        table=next(t for t in tables if "代號" in t.get("fields",[]))
        fields=[str(f).strip() for f in table["fields"]]
        def ix(k): return fields.index(k)
        for raw in table.get("data",[]):
            code=str(raw[ix("代號")]).strip()
            if re.fullmatch(r"\d{4}",code):
                records.append({"market":"TPEX","date":target,"code":code,"name":str(raw[ix("名稱")]).strip(),
                                "close":parse_number(raw[ix("收盤")]),"trade_value_twd":parse_number(raw[ix("成交金額(元)")]),
                                "change_raw":str(raw[ix("漲跌")]).strip()})
        report["sources"]["TPEX"]={"date":target,"raw_rows":len(table.get("data",[])),
            "four_digit_rows":sum(r["market"]=="TPEX" for r in records),"url":tpex_url}
    except Exception as e: report["sources"]["TPEX"]={"error":f"{type(e).__name__}: {e}"}
    report["status"]="DATE_MATCH_CANDIDATES_ONLY" if len(report["sources"])==2 and all("error" not in x for x in report["sources"].values()) and records else "INCOMPLETE"
    report["candidate_rows"]=len(records)
    report["missing_close"]=sum(x["close"] is None for x in records)
    report["missing_trade_value"]=sum(x["trade_value_twd"] is None for x in records)
    report["warning"]="Four-digit codes not yet checked against official ordinary-share master; no strategy output."
    out=Path("results");out.mkdir(exist_ok=True)
    (out/"same_day_quote_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"same_day_four_digit_candidates.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if report["status"]!="DATE_MATCH_CANDIDATES_ONLY": raise SystemExit("Incomplete same-day market snapshot")

if __name__=="__main__": main()
