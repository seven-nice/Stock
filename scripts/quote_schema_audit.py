"""Stage 2: inspect official daily quotes without guessing field semantics.
Read-only, no private data, no trade signals.
"""
import collections
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

URLS = {
    "TWSE_DAILY": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
    "TPEX_DAILY": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
}
DATE_RE = re.compile(r"^(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|1\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{7,8})$")
CODE_RE = re.compile(r"^\d{4}$")

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)

def inspect(name, url):
    data = get_json(url)
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise ValueError(f"{name}: unexpected API shape")
    fields = list(data[0])
    date_fields = [k for k in fields if ("日期" in k or "date" in k.lower() or "年月日" in k)]
    code_fields = [k for k in fields if ("代號" in k or "code" in k.lower() or "stock" in k.lower())]
    summaries = {}
    for k in date_fields:
        counts = collections.Counter(str(r.get(k, "")).strip() for r in data)
        summaries[k] = counts.most_common(12)
    codes = {}
    for k in code_fields:
        values = [str(r.get(k, "")).strip() for r in data]
        codes[k] = {
            "distinct": len(set(values)),
            "four_digit_rows": sum(bool(CODE_RE.fullmatch(v)) for v in values),
            "sample_values": list(dict.fromkeys(values))[:15],
        }
    return {
        "source": name, "url": url, "total_rows": len(data),
        "fields": fields, "date_fields": date_fields,
        "date_distribution_top12": summaries, "code_fields": codes,
        "sample_rows": data[:2],
        "warning": "Rows are not stock counts; four-digit codes are not yet validated as ordinary shares.",
    }

def main():
    output = {"tested_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "sources": {}, "errors": {}}
    for name, url in URLS.items():
        try:
            result = inspect(name, url)
            output["sources"][name] = result
            print(f"{name}: rows={result['total_rows']}, date_fields={result['date_fields']}, code_fields={list(result['code_fields'])}", flush=True)
            print("DATE_COUNTS", name, json.dumps(result["date_distribution_top12"], ensure_ascii=False), flush=True)
            print("CODE_COUNTS", name, json.dumps(result["code_fields"], ensure_ascii=False), flush=True)
            print("FIELDS", name, json.dumps(result["fields"], ensure_ascii=False), flush=True)
        except Exception as e:
            output["errors"][name] = f"{type(e).__name__}: {str(e)[:400]}"
            print(f"{name}: ERROR {e}", flush=True)
    folder = Path("results")
    folder.mkdir(exist_ok=True)
    (folder / "quote_schema_audit.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    if output["errors"] or len(output["sources"]) != len(URLS):
        raise SystemExit("Some source audits failed; inspect saved artifact")

if __name__ == "__main__":
    main()
