# An open benchmark for adverse-media and sanctions screening

**There isn't one.** Not NIST, not TREC, not any regulator. The UK Financial Conduct Authority
has assessed more than 150 firms' sanctions screening since February 2022 and publishes neither
the data nor per-firm results. Vendors advertise "5× deeper coverage" and nobody can check,
because there is nothing to check against.

That absence is worth money to whoever already has customers. This repository is an attempt to
remove it.

It contains **126 labelled entities**, a **vendor-neutral harness**, and a **naive baseline** so
the numbers have a floor to compare against. Point it at any screening system — ours, a
competitor's, your own — and it will produce the same two numbers for all of them.

It also contains a **second, unlabelled measurement** that we have not seen published anywhere:
`population.py` draws companies at random from a national register and reports what share of
*ordinary counterparties* a system alerts on. No labels, no selection, no way to make it easy.
That is the number that decides whether a screening system survives contact with a compliance
team, and it is where we found four defects that the labelled benchmark could not reach.

---

## What it measures

A **screening decision**, not a sentence and not a document. For each labelled entity the
harness asks a system one question — *does this name warrant an alert?* — and compares the
answer to the label. Then it sweeps the threshold, because a single operating point tells you
nothing about the trade a system is making.

Two numbers, both of which a compliance officer can act on:

| | |
|---|---|
| **Recall** | share of entities with a documented predicate-offence enforcement action that reach the alert threshold |
| **False alert** | share of entities with no such documented action that reach it anyway |

Recall is reported **at a fixed false-alert budget**, not as F1. F1 over a corpus whose class
balance is not the operating prevalence is not a number anyone can use.

**Both numbers or neither.** A recall figure published without its false-alert figure is
marketing. Any system can reach 100 % recall by alerting on everything, and in the field that
system gets switched off within a fortnight — which is the actual failure mode the FCA reviews
keep returning to.

## The labels

126 entities in four classes. The labelling rule is deliberately narrow, so that each label can
be defended rather than argued about:

- **positive** (25) — documented, citable enforcement for an AML *predicate* offence: bribery,
  corruption, money laundering, fraud or sanctions, against the entity itself, or for a person
  against that person. Every one carries its citation in `labels.json`.
- **negative** (45) — no such documented matter found at labelling time.
- **ambiguous** (7) — enforcement exists, but of another kind: antitrust, environmental,
  consumer, tax. **Excluded from the headline metrics** and reported separately. Whether these
  should alert is a policy question, not a ground truth, and pretending otherwise would let
  whoever wrote the benchmark choose the winner.
- **not_an_entity** (49) — topics, places, events, concepts. Screening is never run on these.
  A sanity class: an alert here is a defect, but it is not a false positive against a real
  screening population.

An entity whose status could not be verified is labelled `unknown` and excluded; the count of
exclusions is part of the result.

### What is wrong with these labels

Stated up front, because a benchmark that hides its weaknesses is a sales document.

- **They are point-in-time.** Labelled 17 August 2026. A negative can become a positive the day
  after; re-labelling is a maintenance obligation, not a one-off.
- **They are absence-of-evidence for the negatives.** "No documented matter found" is not "no
  matter exists". The negative class is only as good as the search behind it.
- **They over-represent the famous.** Enforcement against large listed companies is easy to
  cite, so the positive class skews large and Western. A system tuned on distinctive corporate
  names will score better here than in a portfolio of small private companies. We measured that
  gap ourselves and it is large — see [RESULTS.md](RESULTS.md).
- **25 positives is a small sample.** With zero errors the upper 95 % bound on the true error
  rate is about 12 %. Treat differences of a few points between systems as noise.

## Running it

```bash
python3 benchmark.py --adapter baseline            # the naive floor
python3 benchmark.py --adapter nodara --host https://your-deployment
python3 benchmark.py --adapter yourmodule:screen   # anything importable

python3 population.py --adapter yourmodule:screen --n 150   # alert load, no labels needed
```

An adapter is one function:

```python
def screen(name: str, subject_type: str = "company") -> dict:
    """Return {"alert": bool} or {"score": float} for one subject name."""
```

That is the entire integration surface — the same one function serves both measurements.
`adapters/keyword_baseline.py` is 40 lines and exists so that nobody reports a number without
knowing what "no system at all" scores.

`population.py` needs no labels at all, so you can run it against your own system today, on a
population you did not choose, without waiting for anyone to agree with our ground truth.

## Licence

- **Code** — MIT. See [LICENSE](LICENSE).
- **Labels and citations** — CC0 1.0 (public domain dedication). See [LICENSE-DATA](LICENSE-DATA).
  Take them, correct them, extend them, sell them. A benchmark nobody can build on is not a
  benchmark.

No third-party text is redistributed here. The harness asks a system about a *name*; it does
not ship article bodies, encyclopaedia text or any vendor's data, and it therefore carries none
of their licence conditions. An optional corpus mode for testing a *text* classifier directly
fetches Wikipedia at run time; that text is CC BY-SA 4.0 and is not part of this repository.

## Who made this and why you should discount it accordingly

Built by [Nodara](https://newsify-vuk0.onrender.com), which sells a screening product and
therefore has an interest in the numbers. Two safeguards against the obvious:

1. The harness is vendor-neutral and the labels are CC0. If our numbers are flattering, run
   your own system and say so.
2. [RESULTS.md](RESULTS.md) reports where our system fails, including four defects this
   benchmark family found in our own product — one of which put Boeing's $2.5bn fraud
   settlement on an unrelated Norwegian holding company.

If you find a mis-labelled entity, open an issue. That is the point.
