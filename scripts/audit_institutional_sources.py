"""Discover official institutional and margin schemas without interpreting unknown fields.
Audit only: never output passing stocks from unverified source schemas.
"""
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

DATES=["2026-11-12","2026-11-11"]
SOURCES={
 "TWSE_T86":("https://www.twse.com.tw/rwd/zh/fund/T86",lambda d:{"response":"json","date":d.replace("-",""),"selectType":"ALLBUT0999"}),
 "TWSE_MARGIN":("https://www.twse.com.tw/rwd/zh/exchangeReport/MI_MARGN",lambda d:{"response":"json","date":d.replace("-",""),"selectType":"ALL"}),
 "TPEX_INST":("https://www.tpex.org.tw/www/zh-tw/3insti/dailyTrade",lambda d:{"response":"json","date":d.replace("-",""),"type":"EW"}),
 "TPEX_MARGIN":("https://www.tpex.org.tw/www/zh-tw/margin/balance",lambda d:{"response":"json","date":d.replace("-",""),"type":"EW"}),
}
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=55) as response:
  raw=response.read(6_000_000)
  return json.loads(raw)
def main():
 results=[]
 for name,(base,params) in SOURCES.items():
  for day in DATES:
   url=base+"?"+urllib.parse.urlencode(params(day))
   record={"source":name,"requested_date":day,"url":url,"verified":False}
   try:
    data=get(url)
    record.update({"keys":list(data)[:20] if isinstance(data,dict) else [],
      "stat":data.get("stat") if isinstance(data,dict) else None,
      "returned_date":data.get("date") if isinstance(data,dict) else None})
    tables=data.get("tables",[]) if isinstance(data,dict) else []
    if tables:
     record["tables"]=[{"title":t.get("title"),"fields":t.get("fields",[])[:35],
       "rows":len(t.get("data",[])),"sample_code":str(t.get("data",[[]])[0][0]) if t.get("data") else None} for t in tables[:8]]
    else:
     record["fields"]=data.get("fields",[]) if isinstance(data,dict) else []
     record["rows"]=len(data.get("data",[])) if isinstance(data,dict) else (len(data) if isinstance(data,list) else 0)
    record["status"]="RESPONSE_INSPECTED"
   except Exception as e:record["status"]="ERROR";record["error"]=f"{type(e).__name__}: {e}"
   print(json.dumps(record,ensure_ascii=False),flush=True)
   results.append(record)
 out=Path("results");out.mkdir(exist_ok=True)
 (out/"institutional_source_audit.json").write_text(json.dumps({"status":"SCHEMA_AUDIT_ONLY","results":results},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
