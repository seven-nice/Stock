"""Strict official TWSE foreign/dealer screen of 2026-11-12 MA-qualified candidates.
Never mistake an absent or mismatched source for a failed trading signal.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

TARGETS={"1802":"台玻","2355":"敬鵬","2465":"麗臺","2471":"資通","3715":"定穎投控","6456":"GIS-KY"}
DATES=("2026-11-11","2026-11-12")
def num(value):
 s=str(value).replace(",","").replace("+","").strip()
 try:return int(s)
 except (ValueError,TypeError):return None
def daily(day):
 params=urllib.parse.urlencode({"response":"json","date":day.replace("-",""),"selectType":"ALLBUT0999"})
 url="https://www.twse.com.tw/rwd/zh/fund/T86?"+params
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=55) as resp:data=json.load(resp)
 if data.get("stat")!="OK" or str(data.get("date"))!=day.replace("-",""):
  raise ValueError("Official TWSE T86 status/date mismatch: "+repr((data.get("stat"),data.get("date"),day)))
 fields=data.get("fields",[])
 needed=["證券代號","外陸資買賣超股數(不含外資自營商)","自營商買賣超股數"]
 if any(f not in fields for f in needed):raise ValueError("Missing expected official columns")
 ids=[fields.index(f) for f in needed]
 result={}
 for row in data.get("data",[]):
  if len(row)<=max(ids):continue
  code=str(row[ids[0]]).strip()
  if code in TARGETS:
   foreign,dealer=num(row[ids[1]]),num(row[ids[2]])
   if foreign is None or dealer is None:raise ValueError("Unparseable values for "+code)
   result[code]={"foreign_net_shares":foreign,"dealer_net_shares":dealer}
 return result
def main():
 output={"signal_date":"2026-11-12","prior_date":"2026-11-11","scope":"six TWSE stocks verified above all four MAs","source":"TWSE T86","status":"INCOMPLETE","results":[],"five_strategy_final":False}
 try:
  previous,current=map(daily,DATES)
  for code,name in TARGETS.items():
   if code not in previous or code not in current:
    output["results"].append({"code":code,"name":name,"status":"MISSING_OFFICIAL_ROW"})
    continue
   f0=previous[code]["foreign_net_shares"]
   f1=current[code]["foreign_net_shares"]
   dealer=current[code]["dealer_net_shares"]
   passed=f0>0 and f1>=2*f0 and dealer>0
   output["results"].append({"code":code,"name":name,"status":"VERIFIED",
      "foreign_prior_shares":f0,"foreign_today_shares":f1,
      "dealer_today_shares":dealer,"institutional_pass":passed})
  output["status"]="VERIFIED" if all(x["status"]=="VERIFIED" for x in output["results"]) else "INCOMPLETE"
 except Exception as exc:output["error"]=f"{type(exc).__name__}: {exc}"
 Path("results").mkdir(exist_ok=True)
 Path("results/twse_institutional_verification.json").write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(output,ensure_ascii=False))
 if output["status"]!="VERIFIED":raise SystemExit("Institutional audit incomplete: no false pass/fail")
if __name__=="__main__":main()
