"""MA verification for TWSE preliminary candidates using official monthly STOCK_DAY.
Independent research module. Fail closed on incomplete history or date mismatch.
TPEx candidates remain PENDING_SOURCE, not rejected.
"""
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

CODES=["1802","2355","2465","2471","3715","4576","6456"]
TARGET=dt.date(2026,11,12)
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
def number(v):
    try:return float(str(v).replace(",","").strip())
    except (ValueError,TypeError):return None
def parse_date(s):
    p=str(s).strip().split("/")
    if len(p)!=3:raise ValueError("Unexpected ROC date "+str(s))
    return dt.date(int(p[0])+1911,int(p[1]),int(p[2]))
def months_back(day,count):
    y,m=day.year,day.month
    for _ in range(count):
        yield dt.date(y,m,1)
        m-=1
        if m==0:m=12;y-=1
def one_stock(code):
    closes={}
    checks=[]
    for month in months_back(TARGET,5):
        url="https://www.twse.com.tw/exchangeReport/STOCK_DAY?"+urllib.parse.urlencode(
            {"response":"json","date":month.strftime("%Y%m%d"),"stockNo":code})
        obj=fetch(url)
        if str(obj.get("stat"))!="OK":
            checks.append({"month":month.isoformat(),"status":str(obj.get("stat"))})
            continue
        fields=obj.get("fields",[])
        if "日期" not in fields or "收盤價" not in fields:raise ValueError("Missing official fields")
        d_i,c_i=fields.index("日期"),fields.index("收盤價")
        for row in obj.get("data",[]):
            day=parse_date(row[d_i]);price=number(row[c_i])
            if day<=TARGET and price is not None and price>0:closes[day]=price
        checks.append({"month":month.isoformat(),"rows":len(obj.get("data",[]))})
    history=sorted(closes.items(),reverse=True)
    out={"market":"TWSE","code":code,"target_date":TARGET.isoformat(),"history_sessions":len(history),"months":checks,"status":"INCOMPLETE"}
    if not history or history[0][0]!=TARGET:
        out["reason"]="Target date missing from official per-stock history"
        return out
    if len(history)<60:
        out["reason"]="Fewer than 60 valid close observations"
        return out
    close=history[0][1]
    averages={f"MA{n}":round(sum(v for _,v in history[:n])/n,6) for n in (5,10,20,60)}
    out.update({"status":"VERIFIED","close":close,"ma":averages,
                "above_all":all(close>v for v in averages.values()),
                "oldest_used":history[59][0].isoformat()})
    return out
def main():
    results=[]
    for code in CODES:
        try:r=one_stock(code)
        except Exception as e:r={"market":"TWSE","code":code,"status":"INCOMPLETE","reason":f"{type(e).__name__}: {e}"}
        print(json.dumps(r,ensure_ascii=False),flush=True)
        results.append(r)
    for code in ("3691","5314"):
        results.append({"market":"TPEX","code":code,"status":"PENDING_SOURCE",
                        "reason":"Official TPEx 60-session per-stock history not yet integrated"})
    output={"target_date":TARGET.isoformat(),"module":"MA_5_10_20_60",
            "rule":"close strictly greater than all four MAs; no bullish-order requirement",
            "results":results,"five_strategy_final":False}
    Path("results").mkdir(exist_ok=True)
    Path("results/ma_verification.json").write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    if not any(r["status"]=="VERIFIED" for r in results):raise SystemExit("No verified TWSE MA result")
if __name__=="__main__":main()
