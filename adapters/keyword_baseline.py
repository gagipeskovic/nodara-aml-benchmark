"""The floor. No model, no data files, twelve English words — so that nobody reports a number
from this benchmark without knowing what "no system at all" scores.

This matters more than it looks. "92 % recall" is meaningless until you know how far a keyword
list gets on its own. If a commercial system cannot beat this by a wide margin on BOTH axes, it
is not doing the work it charges for.

Method: fetch the entity's Wikipedia article as plain text and count distinct adverse keywords.
No subject attribution, no negation handling, no evidence tiering, no recency, no
disambiguation. Deliberately untuned — tuning the floor would defeat its purpose.
"""
import json
import time
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
UA = "aml-benchmark-baseline/1.0 (open AML screening benchmark)"

TERMS = ("fraud", "bribery", "corruption", "money laundering", "sanctions", "convicted",
         "guilty", "indicted", "embezzlement", "misconduct", "scandal", "penalty")

# Two distinct adverse terms anywhere in the article. That is the whole decision rule.
ALERT_AT = 2


def _article(title: str, *, retries: int = 4) -> str:
    """Plain-text article, with backoff.

    A failed fetch RAISES rather than returning empty text. Scoring a network failure as "no
    adverse content" would silently inflate the baseline's precision and deflate its recall,
    which is exactly the kind of quiet corruption a benchmark exists to prevent.
    """
    q = urllib.parse.urlencode({"action": "query", "prop": "extracts", "explaintext": "1",
                                "redirects": "1", "format": "json", "titles": title})
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                pages = (json.load(r).get("query") or {}).get("pages") or {}
            return " ".join((p.get("extract") or "") for p in pages.values())
        except Exception as e:                 # Wikipedia rate-limits a fast loop
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"wikipedia fetch failed for {title!r}: {last}")


def screen(name: str, subject_type: str = "company") -> dict:
    time.sleep(0.4)                            # be a polite client of a free service
    text = _article(name).lower()
    hits = sorted({t for t in TERMS if t in text})
    return {"score": min(1.0, len(hits) / ALERT_AT), "hits": len(hits), "terms": hits,
            "chars": len(text)}
