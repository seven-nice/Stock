"""Daily two-session preliminary screening, not a five-strategy result.

Official dated TWSE/TPEx sources; excludes missing prices and fails closed.
Candidate codes are four-digit securities pending official ordinary-share verification.
"""
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

TZ=dt.timezone(dt.timedelta(hours=8))
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=50) as r: return json.load(r)
def num(v):
    s=str(v).replace(",","").strip()
    try: return float(s)
    except (TypeError,ValueError): return None
def snapshot(day):
    compact=day.strftime("%Y%m%d")
    urls={
        "TWSE":"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?"+urllib.parse.urlencode({"response":"json","date":compact,"type":"ALLBUT0999"}),
        "TPEX":"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?"+urllib.parse.urlencode({"response":"json","date":day.strftime("%Y/%m/%d"),"type":"EW"})
    }
    output={}
    for market,url in urls.items():
        obj=get(url)
        if str(obj.get("date"))!=compact or str(obj.get("stat","")).lower()!="ok":
            raise ValueError(f"{market} date/status invalid for {compact}")
        if market=="TWSE":
            table=next(t for t in obj.get("tables",[]) if "每日收盤行情" in str(t.get("title","")) and "證券代號" in t.get("fields",[]))
            keys={"code":"證券代號","name":"證券名稱","close":"收盤價","value":"成交金額"}
        else:
            table=next(t for t in obj.get("tables",[]) if "代號" in t.get("fields",[]))
            keys={"code":"代號","name":"名稱","close":"收盤","value":"成交金額(元)"}
        fields=[str(x).strip() for x in table["fields"]]
        indexes={k:fields.index(v) for k,v in keys.items()}
        rows={}
        for item in table.get("data",[]):
            code=str(item[indexes["code"]]).strip()
            if not re.fullmatch(r"\d{4}",code):continue
            if code in rows: raise ValueError(f"duplicate code {market} {code}")
            rows[code]={"code":code,"name":str(item[indexes["name"]]).strip(),
                        "close":num(item[indexes["close"]]),"value":num(item[indexes["value"]])}
        if len(rows)<500: raise ValueError(f"{market} too few rows: {len(rows)}")
        output[market]=rows
    return output

def main():
    today=dt.datetime.now(TZ).date()
    end=today if dt.datetime.now(TZ).hour>=18 else today-dt.timedelta(days=1)
    found=[]
    attempts=[]
    for offset in range(0,10):
        day=end-dt.timedelta(days=offset)
        if day.weekday()>=5:continue
        try:
            data=snapshot(day)
            found.append((day,data))
            print("OK",day,{k:len(v) for k,v in data.items()},flush=True)
        except Exception as e:
            attempts.append({"date":day.isoformat(),"error":f"{type(e).__name__}: {str(e)[:160]}"})
            print("SKIP",day,str(e)[:160],flush=True)
        if len(found)==2:break
        time.sleep(0.3)
    out=Path("results");out.mkdir(exist_ok=True)
    audit={"generated_at_taipei":dt.datetime.now(TZ).isoformat(),"attempts":attempts,"status":"INCOMPLETE",
           "warning":"Preliminary price/value screen only. Not ordinary-share verified; no MA, institutions, margin or revenue."}
    candidates=[]
    if len(found)==2:
        (day,latest),(prior_day,previous)=found
        audit.update({"date":day.isoformat(),"previous_date":prior_day.isoformat(),
                      "market_counts":{m:len(latest[m]) for m in latest}})
        for market in ("TWSE","TPEX"):
            for code,row in latest[market].items():
                prior=previous[market].get(code)
                if not prior:continue
                close,prev_close,value,prev_value=row["close"],prior["close"],row["value"],prior["value"]
                if any(v is None for v in (close,prev_close,value,prev_value)) or prev_close<=0 or prev_value<=0:continue
                gain=(close/prev_close-1)*100
                if gain>=5 and value>=700_000_000 and value>=2*prev_value:
                    candidates.append({"market":market,"code":code,"name":row["name"],"date":day.isoformat(),
                        "gain_pct":round(gain,4),"value_twd":value,"value_multiple":round(value/prev_value,4),
                        "preliminary_groups":[key for key,limit,g in [
                            ("MF002",700_000_000,5),("MF026",700_000_000,7),("MF046",700_000_000,7),
                            ("MF050",1_000_000_000,5),("MF066",1_000_000_000,5)]
                            if value>limit and gain>=g]})
        audit["status"]="PRELIMINARY_ONLY"
        audit["preliminary_count"]=len(candidates)
    (out/"preliminary_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"preliminary_candidates.json").write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(audit,ensure_ascii=False),flush=True)
    print("PRELIMINARY_CANDIDATES",json.dumps(candidates,ensure_ascii=False),flush=True)
    if audit["status"]!="PRELIMINARY_ONLY":raise SystemExit("No verified pair of trading dates")

if __name__=="__main__":main()
