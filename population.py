"""Measure a screening system's alert load on a RANDOM population of real companies.

WHY THIS IS A SEPARATE MEASUREMENT

`benchmark.py` asks: given a list of names someone chose, how many of the guilty are caught and
how many of the innocent are flagged? That is the standard shape, and it has a standard flaw —
whoever chose the names chose the difficulty. Every name in it is a company distinctive enough
that a human could label it, which means every name is a company a system finds easy to
identify.

This file asks a different question, and it is the one a compliance officer actually lives with:

    Screen a thousand ordinary counterparties. How many produce an alert?

The names are not chosen. They are drawn at random from a national company register, so they
are what they are: three-employee holding companies, dental practices, taxi firms, and names
that collide with common words. That population is where screening systems fail, and it is
invisible to a benchmark of famous entities.

WHAT WE FOUND BY RUNNING IT, which is the argument for publishing it: four defects that no
labelled benchmark could reach. "OEI HOLDING AS" was given Boeing's $2.5bn settlement (`oei` is
inside `bOEIng`). "OK INVEST AS" was screened against the Gunfight at the O.K. Corral. "FIRST
SEAGULL AS" went red on a seagull that stole a handbag in Bournemouth. "JR HANSEN AS" was given
a US federal fraud sentencing because `hansen` is a common surname. Every one of those needed a
random draw to surface.

THERE IS NO GROUND TRUTH HERE, and that is deliberate. A random draw cannot be labelled — you
would have to research 150 companies. So this measures ALERT LOAD, not accuracy: what share of
ordinary counterparties the system asks a human to look at. Read it together with
`benchmark.py`, never instead of it. A system that alerts on nothing scores perfectly here and
is useless.

SAMPLING — a two-stage cluster sample, described as one rather than dressed up
Norway's Enhetsregisteret refuses deep pagination (`page >= 100` returns HTTP 400), so a simple
random draw over all ~431,000 limited companies is not available through the API. Instead: pick
at least 20 registration dates uniformly at random from a window, take the COMPLETE cohort
registered on each of those days, pool them, and sample from that pool. Every company registered
on a selected day has an equal chance; days are selected with equal probability. That is a
cluster sample, not a simple random sample, and the difference matters if company
characteristics correlate with registration date — they do, weakly, through cohort effects.

The register is free, needs no key, and is published under NLOD 2.0. Any jurisdiction with an
open company register can be added; see `draw_population` for the one function to replace.

USAGE
    python3 population.py --adapter baseline --n 150
    python3 population.py --adapter nodara --host https://your-deployment --n 150
    python3 population.py --adapter yourmodule:screen --n 150 --out rows.json

Pacing defaults to 1.5 s between subjects, and HTTP 429 is obeyed via `Retry-After`. An earlier
unpaced run lost 50 of 70 requests and measured nothing except a deployment's concurrency limit.
"""
from __future__ import annotations

import argparse
import importlib
import json
import random
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BRREG = "https://data.brreg.no/enhetsregisteret/api/enheter"
WINDOW = (date(2010, 1, 1), date(2024, 6, 30))
SEED = 17

try:
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:                                  # noqa: BLE001
    _SSL = ssl.create_default_context()


def _get_json(url: str, timeout: float = 30.0):
    req = urllib.request.Request(url, headers={"User-Agent": "aml-benchmark/1.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return json.load(r)


def draw_population(n: int, *, seed: int = SEED) -> list[dict]:
    """A two-stage cluster sample of live Norwegian limited companies.

    Replace this one function to measure another jurisdiction. It must return dicts with at
    least `name`; everything else is reporting detail.
    """
    rnd = random.Random(seed)
    span = (WINDOW[1] - WINDOW[0]).days
    pool: list[dict] = []
    seen: set[str] = set()
    # A fixed number of CLUSTERS, not "keep going until the pool is big enough". The first
    # version of this stopped after two days, because ~85 companies are registered per day and
    # the pool target was met immediately — a two-cluster sample, where every company shared one
    # of two registration dates. More clusters is the whole defence against cohort effects.
    clusters = max(20, n // 3)
    tries = 0
    while len(set(x["registered"] for x in pool)) < clusters and tries < clusters * 3:
        tries += 1
        d = WINDOW[0] + timedelta(days=rnd.randrange(span))
        q = urllib.parse.urlencode({
            "organisasjonsform": "AS", "size": 100,
            "fraRegistreringsdatoEnhetsregisteret": d.isoformat(),
            "tilRegistreringsdatoEnhetsregisteret": d.isoformat()})
        try:
            data = _get_json(f"{BRREG}?{q}")
        except Exception as e:                     # noqa: BLE001
            print(f"  (register {d}: {e})", file=sys.stderr)
            continue
        for u in (data.get("_embedded") or {}).get("enheter", []) or []:
            orgnr = str(u.get("organisasjonsnummer") or "")
            if u.get("slettedato") or orgnr in seen or not u.get("navn"):
                continue
            seen.add(orgnr)
            pool.append({"id": orgnr, "name": u["navn"],
                         "registered": u.get("registreringsdatoEnhetsregisteret"),
                         "bankrupt": bool(u.get("konkurs"))})
    rnd.shuffle(pool)
    return pool[:n]


# Same short names benchmark.py accepts, so a reader does not have to learn two vocabularies.
_BUNDLED = {"baseline": "adapters.keyword_baseline", "nodara": "adapters.nodara"}


def load_adapter(spec: str):
    """`baseline`, `nodara`, or `yourmodule:function`. Same contract as benchmark.py."""
    if ":" in spec:
        mod, fn = spec.split(":", 1)
        m = importlib.import_module(mod)
        return getattr(m, fn), getattr(m, "configure", None)
    m = importlib.import_module(_BUNDLED.get(spec, f"adapters.{spec}"))
    return m.screen, getattr(m, "configure", None)


def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    """95 % interval for a proportion. Wilson, not normal approximation: at k=0 or small n the
    normal interval is wrong in a way that flatters whoever is reporting."""
    if n == 0:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    s = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - s) * 100, min(1.0, c + s) * 100)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--host", default=None)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="score at or above this counts as an alert")
    ap.add_argument("--pace", type=float, default=1.5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    screen, configure = load_adapter(a.adapter)
    if configure and a.host:
        configure(host=a.host)

    print(f"drawing {a.n} random Norwegian limited companies (seed {a.seed}) ...")
    subjects = draw_population(a.n, seed=a.seed)
    if not subjects:
        print("The draw returned nothing. If the errors above are TLS certificate failures, "
              "this Python has no root certificates: pip3 install certifi", file=sys.stderr)
        return 2
    print(f"  {len(subjects)} drawn\n")

    rows, errors = [], 0
    for i, s in enumerate(subjects, 1):
        got = None
        for attempt in range(4):
            try:
                got = screen(s["name"], "company")
                break
            except urllib.error.HTTPError as e:
                # Obey the server. A 429 that carries Retry-After is telling you exactly how
                # long to wait; guessing is how a measurement loses a third of its sample.
                hdr = (e.headers or {}).get("Retry-After") if hasattr(e, "headers") else None
                wait = int(hdr) if str(hdr or "").isdigit() else 60 * (attempt + 1)
                print(f"    HTTP {e.code}, waiting {min(wait, 900)}s", file=sys.stderr)
                time.sleep(min(wait, 900))
            except Exception as e:                 # noqa: BLE001
                print(f"    {s['name']}: {type(e).__name__}", file=sys.stderr)
                time.sleep(10)
        if got is None:
            errors += 1
            continue
        score = float(got.get("score", 1.0 if got.get("alert") else 0.0))
        rows.append({**s, "score": score, "alert": score >= a.threshold,
                     **({"light": got["light"]} if "light" in got else {})})
        print(f"{i:4d}/{len(subjects)} {s['name'][:34]:34s} "
              f"{'ALERT' if rows[-1]['alert'] else '  .  '}  {score:.2f}")
        if a.out:
            json.dump(rows, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if a.pace:
            time.sleep(a.pace)

    n = len(rows)
    if not n:
        print("no results", file=sys.stderr)
        return 1
    k = sum(1 for r in rows if r["alert"])
    lo, hi = wilson(k, n)
    print("\n" + "=" * 74)
    print(f"ADAPTER          {a.adapter}   threshold {a.threshold}")
    print(f"POPULATION       {n} randomly drawn Norwegian limited companies "
          f"(seed {a.seed}){f', {errors} failed' if errors else ''}")
    if errors:
        print("  Subjects are missing. The rate below describes the ones that were measured "
              "and assumes the failures are not systematically different.")
    print()
    print(f"ALERT LOAD       {k}/{n} = {100 * k / n:.1f} %      95 % CI {lo:.1f}–{hi:.1f} %")
    print()
    print("There is NO ground truth in this sample, so this is not an accuracy figure. It is")
    print("the share of ordinary counterparties the system asks a human to look at. A system")
    print("that alerts on nothing scores 0 % here and is useless — read it next to")
    print("benchmark.py, never instead of it.")
    if k:
        print("\nAlerted:")
        for r in rows:
            if r["alert"]:
                print(f"    {r['name'][:40]:40s} {r.get('light') or r['score']}")
    if a.out:
        print(f"\nraw rows: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
