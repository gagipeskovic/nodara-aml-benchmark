"""Vendor-neutral harness for the adverse-media screening benchmark.

One question per entity — does this name warrant an alert? — compared against a label, swept
across thresholds. Any system that can answer that question can be scored, through an adapter
of one function.

    python3 benchmark.py --adapter baseline
    python3 benchmark.py --adapter nodara --host https://your-deployment
    python3 benchmark.py --adapter mypackage.mymodule:screen

Reports recall at a fixed false-alert budget rather than F1: F1 over a corpus whose class
balance is not the operating prevalence is not a number anyone can act on. And it reports both
directions always — a recall figure without its false-alert figure is marketing, since any
system reaches 100 % recall by alerting on everything.

MIT licensed. Labels are CC0. See README.md.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(HERE, "labels.json")


def load_labels() -> list:
    with open(LABELS, encoding="utf-8") as fh:
        return json.load(fh)["entities"]


def load_adapter(spec: str, **kwargs):
    """'baseline' | 'nodara' | 'package.module:function'."""
    # Short names map to the bundled adapters; anything with a colon is imported verbatim, so
    # a third party never has to put a file in this repository to be measured by it.
    _BUNDLED = {"baseline": "adapters.keyword_baseline", "nodara": "adapters.nodara"}
    if ":" in spec:
        mod, _, fn = spec.partition(":")
    else:
        mod, fn = _BUNDLED.get(spec, f"adapters.{spec}"), "screen"
    sys.path.insert(0, HERE)
    m = importlib.import_module(mod)
    f = getattr(m, fn)
    if hasattr(m, "configure"):
        m.configure(**kwargs)
    return f


def _alert(result, threshold: float) -> bool:
    """An adapter may answer with a boolean or a score. Both are allowed; a score lets the
    harness sweep, which is the more informative answer."""
    if result is None:
        return False
    if "alert" in result and "score" not in result:
        return bool(result["alert"])
    return float(result.get("score") or 0.0) >= threshold


def rule_of_three(k: int, n: int) -> str:
    """Upper 95 % bound. Exact when k == 0; otherwise a normal approximation, flagged as one."""
    if not n:
        return "-"
    if k == 0:
        return f"<= {300 / n:.1f} %"
    p = k / n
    return f"{100 * p:.1f} % +/- {196 * ((p * (1 - p) / n) ** 0.5):.1f} pp"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="baseline")
    ap.add_argument("--host", default=None, help="passed to the adapter's configure()")
    ap.add_argument("--api-key", default=None, help="passed to the adapter's configure()")
    ap.add_argument("--thresholds", default="0.3,0.5,0.7,0.9")
    ap.add_argument("--limit", type=int, default=0, help="score only the first N (for a smoke test)")
    ap.add_argument("--classes", default=None,
                    help="comma-separated label classes to score, e.g. positive,negative. "
                         "Scoring a subset is legitimate but the omission must be reported, "
                         "so the harness prints it.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--resume", default=None,
                    help="an earlier --out file; entities already scored there are not "
                         "re-queried. Screening APIs bill per query and a re-run is a new bill.")
    ap.add_argument("--pace", type=float, default=1.5,
                    help="seconds between requests. Measured 17 Aug 2026: a benchmark loop with "
                         "no pacing drove 50 of 70 requests to HTTP 502, because each screening "
                         "fans out to several upstream sources. Politeness is part of the "
                         "method, not an optimisation.")
    a = ap.parse_args()

    cfg = {k: v for k, v in (("host", a.host), ("api_key", a.api_key)) if v}
    screen = load_adapter(a.adapter, **cfg)
    rows = load_labels()
    if a.classes:
        want = {c.strip() for c in a.classes.split(",")}
        skipped = [r for r in rows if r["label"] not in want]
        rows = [r for r in rows if r["label"] in want]
        print(f"KLASSER BEGRENSET til {sorted(want)} — {len(skipped)} entitet(er) utelatt. "
              f"Et delvis kjørt sett er et delvis resultat.")
    if a.limit:
        rows = rows[:a.limit]

    done = {}
    if a.resume and os.path.exists(a.resume):
        with open(a.resume, encoding="utf-8") as fh:
            done = {r["name"]: r["result"] for r in json.load(fh)
                    if r.get("result") is not None}
        print(f"gjenopptar: {len(done)} allerede scoret, spørres ikke på nytt")

    print(f"{len(rows)} entiteter, adapter '{a.adapter}'\n")
    results, errors = [], 0
    t0 = time.time()
    for i, r in enumerate(rows, 1):
        if r["name"] in done:
            results.append({**r, "result": done[r["name"]]})
            continue
        subject_type = "person" if r.get("type") == "person" else "company"
        out = None
        for attempt in range(3):
            try:
                out = screen(r["name"], subject_type)
                break
            except Exception as e:
                last = e
                time.sleep(5 * (attempt + 1))
        if out is None:
            print(f"  FEIL {r['name']}: {last}", file=sys.stderr)
            errors += 1
        results.append({**r, "result": out})
        time.sleep(a.pace)
        if i % 20 == 0:
            print(f"  {i}/{len(rows)} ...", flush=True)

    thresholds = [float(x) for x in a.thresholds.split(",")]
    scored = [r for r in results if r["result"] is not None]
    pos = [r for r in scored if r["label"] == "positive"]
    neg = [r for r in scored if r["label"] == "negative"]
    amb = [r for r in scored if r["label"] == "ambiguous"]
    nae = [r for r in scored if r["label"] == "not_an_entity"]

    print("\n" + "=" * 78)
    print(f"{'terskel':>8s}  {'recall (positive)':>20s}  {'falsk varsel (negative)':>24s}"
          f"  {'tvetydig':>9s}  {'ikke-entitet':>13s}")
    best = None
    for t in thresholds:
        rp = sum(1 for r in pos if _alert(r["result"], t))
        rn = sum(1 for r in neg if _alert(r["result"], t))
        ra = sum(1 for r in amb if _alert(r["result"], t))
        rx = sum(1 for r in nae if _alert(r["result"], t))
        print(f"{t:8.2f}  {rp:6d}/{len(pos):<3d} {100*rp/max(1,len(pos)):6.1f} %"
              f"  {rn:8d}/{len(neg):<3d} {100*rn/max(1,len(neg)):6.1f} %"
              f"  {ra:5d}/{len(amb):<3d}  {rx:6d}/{len(nae):<3d}")
        if rn == 0 and (best is None or rp > best[1]):
            best = (t, rp)

    print("\nHOVEDTALL")
    if best:
        t, rp = best
        print(f"  Recall ved NULL falske varsler: {100*rp/max(1,len(pos)):.1f} %  (terskel {t})")
        print(f"  Øvre 95 %-grense for falsk varsel: {rule_of_three(0, len(neg))}")
    else:
        print("  Ingen terskel gir null falske varsler på det negative settet.")
    print(f"  Scoret {len(scored)} av {len(rows)}"
          + (f", {errors} feilet" if errors else ""))
    print("  Tvetydige er holdt UTENFOR hovedtallene med hensikt: om de bør varsle er et")
    print("  policyspørsmål, ikke en fasit.")
    print(f"  tid: {time.time()-t0:.0f} s")

    misses = [r["name"] for r in pos if best and not _alert(r["result"], best[0])]
    if misses:
        print(f"\nBOMMET ved terskelen ({len(misses)}): " + ", ".join(misses[:12]))

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=1)
        print(f"\nrådata: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
