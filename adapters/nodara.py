"""Adapter for a Nodara deployment. Reference implementation of the adapter contract.

Nodara returns a full risk overview; the benchmark asks a narrower question, so this maps the
adverse-media traffic light onto a score: red = 1.0, amber = 0.6, green = 0.0. That mapping is
part of the measurement and is stated here rather than hidden, so a reader can disagree with it.
"""
import json
import urllib.request

_HOST = "https://newsify-vuk0.onrender.com"
_LIGHT = {"red": 1.0, "amber": 0.6, "green": 0.0, "grey": 0.0}


def configure(host: str = None, **_):
    global _HOST
    if host:
        _HOST = host.rstrip("/")


def screen(name: str, subject_type: str = "company") -> dict:
    body = json.dumps({"name": name, "type": subject_type}).encode()
    req = urllib.request.Request(f"{_HOST}/api/v1/aml/screen", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    light = ((d.get("risk_overview") or {}).get("adverse_media") or {}).get("status")
    return {"score": _LIGHT.get(light, 0.0), "light": light}
