"""Read-only connectivity/schema probe. No trading or private data."""
import datetime as dt
import json
import time
import urllib.request
from pathlib import Path

ENDPOINTS = {
    "TWSE_DAILY": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
    "TPEX_DAILY": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
    "TWSE_COMPANIES": "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
    "TPEX_COMPANIES": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
}

def probe(name, url):
    row = {"name": name, "url": url}
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MarketDataProbe/1.0)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read(20_000_000)
            row.update(http_status=response.status,
                       content_type=response.headers.get("Content-Type"),
                       bytes_read=len(raw))
        payload = json.loads(raw)
        row["json_type"] = type(payload).__name__
        row["row_count"] = len(payload) if isinstance(payload, (list, dict)) else None
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            row["sample_fields"] = list(payload[0])[:40]
            row["sample_date_fields"] = {
                k: str(v)[:100] for k, v in payload[0].items()
                if "date" in k.lower() or "日期" in k
            }
        row["ok"] = isinstance(payload, list) and len(payload) > 0
    except Exception as exc:
        row.update(ok=False, error_type=type(exc).__name__, error=str(exc)[:500])
    row["seconds"] = round(time.monotonic() - start, 2)
    print(name, "PASS" if row["ok"] else "FAIL", row.get("row_count"),
          row.get("error", ""), flush=True)
    return row

def main():
    rows = [probe(name, url) for name, url in ENDPOINTS.items()]
    folder = Path("results")
    folder.mkdir(exist_ok=True)
    report = {
        "tested_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "Connectivity/schema only; not a stock screening result.",
        "results": rows,
    }
    (folder / "api_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "api_probe.md").write_text(
        "# TWSE/TPEx API probe\n\n" +
        "\n".join(f"- {x['name']}: {'PASS' if x['ok'] else 'FAIL'}; "
                  f"rows={x.get('row_count', '?')}; error={x.get('error', 'none')}"
                  for x in rows) + "\n", encoding="utf-8"
    )
    if not all(x["ok"] for x in rows):
        raise SystemExit("API probe incomplete; see artifact results/api_probe.json")

if __name__ == "__main__":
    main()
