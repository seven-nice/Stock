"""Probe dated official market-wide endpoints before choosing a backfill strategy."""
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

TESTS = {
    "TWSE_20261112": ("https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
                      {"response":"json","date":"20261112","type":"ALLBUT0999"}),
    "TPEX_20261111": ("https://www.tpex.org.tw/www/zh-tw/afterTrading/otc",
                      {"response":"json","date":"2026/11/11"}),
    "TPEX_20261112": ("https://www.tpex.org.tw/www/zh-tw/afterTrading/otc",
                      {"response":"json","date":"2026/11/12"}),
    "TPEX_ROC_1151112": ("https://www.tpex.org.tw/www/zh-tw/afterTrading/otc",
                      {"response":"json","date":"115/11/12"}),
    "TPEX_COMPACT_20261112": ("https://www.tpex.org.tw/www/zh-tw/afterTrading/otc",
                      {"response":"json","date":"20261112"}),
    "TPEX_ROC_COMPACT": ("https://www.tpex.org.tw/www/zh-tw/afterTrading/otc",
                      {"response":"json","date":"1151112"}),
}

def run():
    result={"tested_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"checks":{}}
    for name,(base,params) in TESTS.items():
        url=base+"?"+urllib.parse.urlencode(params)
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=40) as response:
                payload=response.read(1500000)
                ctype=response.headers.get("Content-Type","")
            parsed=json.loads(payload)
            if not isinstance(parsed,dict): raise ValueError("Expected JSON object")
            tables=parsed.get("tables",[])
            result["checks"][name]={"status":"JSON_OK","url":url,"content_type":ctype,
                "keys":list(parsed.keys()),"stat":parsed.get("stat"),
                "date":parsed.get("date"),"title":parsed.get("title"),
                "data_rows":len(parsed.get("data",[])) if isinstance(parsed.get("data"),list) else None,
                "table_count":len(tables) if isinstance(tables,list) else None,
                "table_summaries":[{"title":t.get("title"),"fields":t.get("fields",[])[:12],
                     "rows":len(t.get("data",[]))} for t in tables[:12] if isinstance(t,dict)]}
        except Exception as e:
            result["checks"][name]={"status":"FAILED","url":url,"error":f"{type(e).__name__}: {str(e)[:300]}"}
        print(name,json.dumps(result["checks"][name],ensure_ascii=False),flush=True)
    Path("results").mkdir(exist_ok=True)
    Path("results/dated_source_probe.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":run()
