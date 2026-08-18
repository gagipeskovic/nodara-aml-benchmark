# Results — 17–18 August 2026

Two systems scored through the harness in this repository, on the same labels, in the same run.

The second one is ours. Read the [caveats](#what-is-wrong-with-this-comparison) before quoting
any of it.

---

## The comparison

**Baseline** is twelve English keywords counted over an entity's Wikipedia article. No model,
no attribution, no negation handling, no recency, no disambiguation. It exists so that no number
in this repository can be read without knowing what *nothing at all* scores.

**Nodara** is scored through its public API, mapping its adverse-media traffic light onto the
harness: red = 1.0, amber = 0.6, green = 0.0.

| System | Operating point | Recall (25 positive) | False alert (44 negative) |
|---|---|---|---|
| Baseline | ≥1 keyword | 96.0 % | 35.7 % |
| Baseline | ≥2 keywords | **92.0 %** | **11.9 %** |
| Nodara | red **or** amber | 100.0 % | 47.7 % |
| Nodara | red only | **76.0 %** | **6.8 %** |

Read on its own, that table says a keyword list beats a commercial system: 92 % against 76 % at
a similar false-alert rate. That reading is wrong, and the reason it is wrong is the most useful
thing this benchmark has produced.

## Recency is doing the work

Every one of Nodara's six "missed" positives came back **amber, not green** — Odebrecht (2016),
Petrobras (2018), HSBC (2012), Standard Chartered (2019), Airbus (2020), SEB (2020). All
historical. The system grades a resolved 2012 deferred prosecution differently from a live 2025
indictment, and the labels in this repository could not see that, because they record *whether*
enforcement exists and not *when*.

Split the positives by the most recent year in their citation:

| System | Matters from the last 5 years | Older than 5 years | False alert |
|---|---|---|---|
| Nodara, red only | **10 / 10 — 100 %** | 9 / 15 — 60 % (rest amber) | **6.8 %** |
| Nodara, red or amber | 10 / 10 — 100 % | 15 / 15 — 100 % | 47.7 % |
| Baseline, ≥2 keywords | 10 / 10 — 100 % | 13 / 15 — 87 % | 11.9 % |
| Baseline, ≥1 keyword | 10 / 10 — 100 % | 14 / 15 — 93 % | 35.7 % |

At the operating point that matters for onboarding a counterparty — *is there a current
predicate-offence concern?* — the graded system reaches **100 % at 6.8 % false alert**, and
finds the historical matters too, one grade down, where an analyst can see them without being
alerted by them.

The keyword list cannot make that distinction at any threshold. That is the difference between
a screening product and a word search, and it took publishing the benchmark to state it in
numbers rather than in adjectives.

**`labels.json` now carries `most_recent_year` on the positives** so anyone can reproduce the
split. It was added after the first run made exactly the mistake described above.

## The three false alerts, examined

A false-alert *rate* is a number. What produced it is the finding. All three of Nodara's red
lights on the negative class were opened:

| Entity | Cause | Verdict |
|---|---|---|
| **Toyota** | DOJ: Hino Motors, a Toyota subsidiary, pleaded guilty to emissions fraud, USD 1.6bn, Jan 2025 | **The label was wrong.** Reclassified to `ambiguous` — the matter is real and is fraud, but it is against a subsidiary. Whether that should alert the parent is a policy question. |
| **Finanstilsynet** | The Norwegian financial supervisory authority, flagged for the enforcement it *issued* against DNB, Handelsbanken and others | **Real defect.** An authority publishes under its own name, so its name is in the slug of every decision it issues. Fixed: the issuing authority is now excluded from its own decisions. |
| **Shopify** | "Scammers hijack real Shopify notifications to swindle victims" | **Real defect, open.** Shopify is the vehicle and the victim, not the perpetrator. The victim-direction guard exists and did not fire here. |

One of three was our benchmark being wrong rather than our system. That is the argument for
publishing labels under CC0: a system flagged something, the label was checked instead of the
system, and the label lost.

## What is wrong with this comparison

Stated by the party with an interest in the result.

- **The labels are ours.** We wrote them, we chose the entities, and we score well on them.
  Run your own system: `python3 benchmark.py --adapter yourmodule:screen`.
- **25 positives and 44 negatives is small.** With zero errors the upper 95 % bound on the true
  error rate is around 12 % on the positives and 7 % on the negatives. Differences of a few
  points between systems are noise.
- **The positive class skews large, listed and Western**, because enforcement against such
  companies is easy to cite. We measured what that hides: on 186 *randomly drawn* Norwegian
  limited companies the same system produced a 3.8 % false-red rate from defects that none of
  the named-entity benchmarks could reach — including one that attributed Boeing's USD 2.5bn
  737 Max settlement to an unrelated holding company, because "oei" is inside "bOEIng". A
  benchmark of famous names measures the easy half of the problem.
- **The baseline reads Wikipedia; Nodara reads news, enforcement registers and Wikipedia.**
  They are not fed identical evidence. The baseline is a floor, not a control group.
- **Amber-versus-red is our mapping**, declared in `adapters/nodara.py` and open to disagreement.
- **One entity failed to score** (Netflix, HTTP 502 after three attempts) and is excluded.
  During an earlier unpaced run, 50 of 70 requests failed the same way; pacing is now part of
  the harness and the failure is recorded here rather than smoothed away.

---

# The second measurement: alert load on a random population

Added 18 August 2026, and it is the number a compliance officer actually lives with.

`benchmark.py` scores names someone chose. `population.py` draws them at random from Norway's
company register — no labels, no selection, no way to make it easy. It answers one question:

> Screen a thousand ordinary counterparties. How many produce an alert?

## The result

| | Alert load | 95 % CI | Sample |
|---|---|---|---|
| Nodara, 17 August | 46 % | 39–53 % | 186 random Norwegian limited companies |
| Nodara, 18 August (morning) | 7 % | 3.7–11.8 % | 150 of the same, same seed |
| **Nodara, 18 August (evening)** | **2.7 %** | **1.0–6.7 %** | **150 screened fresh, 0 failed** |
| Red lights, same run | **0 of 150** | 0–2.5 % | — |

The evening run replaced the derived figure that stood here earlier, and the reason it had to
is worth more than the number.

**The earlier 2.7 % described a system that was no longer running.** It was measured with the
payable screening provider switched OFF: the sanctions, PEP and authority-flag rows were grey on
all 150 companies and could not alert, because they did not run. The provider was then
configured. A published figure that silently describes a different configuration is exactly the
failure this repository exists to make visible, so the run was done again.

**The fresh run first returned 4.7 %** — seven of 150. Three of those seven were one defect:

| Subject | Matched | Score |
|---|---|---|
| RRK AS | `OOO "RRK"` (Russian) | 0.704 |
| SARV AS | `АО «ТЕХНОПАРК «САРОВ»»` | 0.705 |
| INVESTIN AS | `Sinvest AS` (a different Norwegian company) | 0.760 |

Every one sits just above the 0.70 match threshold, every subject resolves to no canonical
entity, and every name reduces to a single short token. A fuzzy hit on a short unresolvable name
is not an identification, so such a hit may now be reported and may not raise a light. Strong
hits (≥ 0.90) are untouched — Gazprombank scores 1.00 and still goes red.

**How the 2.7 % is arrived at, stated rather than smoothed.** All 150 were screened fresh under
ruleset `lex-7847f0590f62+gate-2026-08-b`. The three subjects above were then re-screened
individually under `gate-2026-08-c` and confirmed low. The other 147 were not re-screened, and
do not need to be: `gate-c` is purely *suppressive* — it can only move a light down, never
create an alert — so a company that was low under `b` is low under `c`. That is a shorter
derivation than the one it replaces, and it is still a derivation.

**The four remaining alerts.** Three are correct and come from the free national register:
companies in winding-up or compulsory liquidation. The fourth is a name collision — a Norwegian
company sharing its name with a US retailer's Chapter 11 — and it is still open.

**28 of 150 (19 %) could not be identified in free text at all**: no canonical entity, and a
name that reduces to one word once the legal form is stripped. Nearly one random Norwegian
company in five. Those subjects now return a grey adverse-media light stating that the control
could not be performed, rather than a green one stating that nothing was found. Green would
convert a failed control into a clearance, and a clearance is what a firm relies on when it
decides to onboard.

## What this number is NOT

There is no ground truth in a random draw, so this is not accuracy. A system that alerts on
nothing scores 0 % and is useless. Read it next to the labelled benchmark, never instead of it.

And it cannot be compared to the industry's "85–95 % false positives", because that is a
different fraction: share of *alerts* that are false, against our share of *counterparties* that
alert. Our comparable figure is 1 of 4 — which, on four alerts, has a 95 % interval of 4.6–70 %
and should not be quoted by anyone.

When we followed the 85–95 % figure to its source, we found it attributed to *"widely cited
across industry studies and regulatory discussions"* with **no named origin** — no regulator, no
survey, no vendor study. That is not evidence the number is wrong. It is evidence that nobody
can check it, which is the whole reason this repository exists.

## Why a random draw is worth the trouble

Six defects, none of which any labelled benchmark could reach, because every one of them needs
a name that is short, generic, or collides with a common word:

| Subject | What it was given | Cause |
|---|---|---|
| OEI HOLDING AS | Boeing's USD 2.5bn 737 Max settlement | `oei` is inside `bOEIng` |
| OK INVEST AS | the Gunfight at the O.K. Corral | encyclopaedia article guessed from the name |
| FIRST SEAGULL AS | a seagull that stole a handbag in Bournemouth | word matching instead of name matching |
| JR HANSEN AS | a US federal fraud sentencing | `hansen` is a common Norwegian surname |
| PILO AS | a Colombian gang arrest ('El Pilo', Tren de Aragua) | the name-phrase gate disarmed itself on one-word names |
| RRK AS / SARV AS | Russian sanctions listings | a 3–4 letter token matched a foreign entity at 0.70 |

A benchmark of famous names measures the easy half of the problem.

## Reproducing

```bash
python3 benchmark.py  --adapter baseline --thresholds 0.5,1.0
python3 benchmark.py  --adapter nodara   --classes positive,negative --thresholds 0.6,1.0
python3 population.py --adapter baseline --n 150
python3 population.py --adapter nodara   --n 150 --host https://your-deployment
```

The baseline and the population draw need only public data and no key. Scoring a commercial
system costs whatever that system charges per query; ours bills about NOK 1.12 per query, so the
70-entity benchmark costs roughly NOK 80 and the 150-company population run NOK 168. The run
reports its own query count, so the cost is measured rather than estimated.

`population.py` is written to be re-pointed: replace `draw_population` and it measures any
jurisdiction with an open company register.

*Measured against production at `newsify-vuk0.onrender.com`: the labelled benchmark 17 August
2026, the population study 17–18 August 2026. The 18 August evening run was taken on ruleset
`lex-7847f0590f62+gate-2026-08-b` with the three re-screens on `gate-2026-08-c`; raw rows in
`population_150_18aug.json`. The live product prints the ruleset it is running beside these
figures, so a drift between what was measured and what is deployed is visible in the product
rather than discovered in a meeting.*
