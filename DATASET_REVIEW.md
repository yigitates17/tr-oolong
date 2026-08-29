# Turkish source review — the short version

**One document for every source question.** Absorbs the former
`PAIRING_SEARCH.md` and `MUSTERI_TRIAL.md`.

**Question asked:** is We-Bears good enough, and is anything better available?
**Answer:** We-Bears is the weakest source in the repo and is already labelled
secondary. Nothing found beats the primary pair. One candidate would improve on
We-Bears specifically, at the cost of four question families.

Measured 2026-08-25 across `ytu-ce-cosmos`, `turkish-nlp-suite` and `Trendyol`.

---

## The table

`R_max` = largest haystack the pool can support (`smallest_class × K` records).
`style` = how much of the label a length-and-punctuation-only classifier
recovers, over the majority baseline. `spread` = longest class's mean word count
÷ shortest's.

| source | rows | classes | imbalance | ceiling | style | spread | licence |
|---|---|---|---|---|---|---|---|
| **`vitamins_tr`** (in use, primary) | 43,043 | 3 | 2.3x | 602K | +0.048 | 1.5x | CC-BY-SA-4.0 |
| ~~We-Bears~~ (**withdrawn v0.5.0**) | 25,186 | 3 | 4.1x | 527K | **+0.120** | **3.6x** | Apache-2.0 |
| MüşteriYorumları | 73,920 | 3 | 3.4x | **970K** | **+0.004** | **1.2x** | CC-BY-SA-4.0 |
| BüyükSinema | 67,328 | **10** | 10.1x | **1.5M** | +0.000 | 1.6x | CC-BY-SA-4.0 |
| TurkishHateMap | 42,175 | 4 | 32.9x | 414K | +0.000 | **6.8x** | CC-BY-SA-4.0 |
| guardrail-tr (top-5 classes) | 114,353 | 5 | **59.2x** | **259K** | +0.000 | 1.4x | Apache-2.0 |

---

## Verdicts, one line each

**`vitamins_tr` — keep as primary.** Not because it wins on every number, but
because it is the only Turkish source with a **brand column that is statistically
independent of the label** (normalised MI 0.022). That independence is what makes
`entity_count`, `entity_argmax`, `pairwise` and `top_k` possible. Every other
candidate has no entity column or a correlated one.

**We-Bears — WITHDRAWN 2026-08-30.** Three independent marks against it:
a +0.120 style shortcut (7x its English twin's), a 3.6x length spread, and **0
conflicting labels across 262 duplicate-text groups** where the human-annotated
airline twin has 17.1%. That last one means labels are a deterministic function
of text, which humans do not produce. Its provenance is undocumented upstream.

**MüşteriYorumları — the only genuine upgrade over We-Bears.** Better on every
axis: style +0.004 vs +0.120, spread 1.2x vs 3.6x, ceiling 970K vs 527K, and the
label is the customer's own star rating rather than undocumented. **Cost: no
product or brand column, so it carries 6 of 10 families.** That is the whole
trade-off.

**BüyükSinema — rejected.** 10 classes and a 1.5M ceiling are attractive, but
10x imbalance and **93.7% of duplicate-text rows carry conflicting stars** —
the same review text rated 7 by one user and 8 by another. That is real
subjectivity in a 10-point scale, and it would sit directly under our numeric
metric.

**TurkishHateMap — rejected.** Human-annotated by a professional team, which is a
genuine plus, but 33x imbalance, a 414K ceiling, a **6.8x length spread** (the
worst measured), and target group correlates with label (MI 0.151) so it gives no
usable entity axis. BERTurk reaches only 0.61 on it, meaning the labels are
highly subjective. Distributing hate-speech text is a separate cost.

**guardrail-tr — rejected for this benchmark, and the reasoning is worth reading
because it is not the obvious one.**

---

## guardrail-tr in detail

You asked about this one specifically, and it is a reasonable thing to want: YTU
COSMOS is a serious lab, the licence is Apache-2.0, and 405K rows sounds like
plenty.

**What is genuinely good about it.** The `language` column separates
**140,559 Turkish-origin rows** from the translated ones, which removes the
translation confound I originally rejected it for — that objection was wrong and
is withdrawn. Its style shortcut is +0.000 and its label leakage is 0.12%, both
excellent. A 10-class hazard taxonomy would sit usefully between our 3 and 48.

**Why it still cannot be used here: it is too skewed to make long haystacks.**
The Turkish-origin single-category rows break down as:

| category | rows |
|---|---|
| SAFE | 69,482 |
| HARASSMENT_OFFENSIVE | 34,857 |
| HATE_DISCRIMINATION | 6,668 |
| MISINFORMATION_POLITICAL | 2,173 |
| PRIVACY_VIOLATION | 1,691 |
| VIOLENT_CRIMES | 1,173 |
| SEXUAL_CONTENT_ADULT, SELF_HARM, CSAE, NON_VIOLENT, INJECTION | 21 – 900 each |

A haystack of *R* records over *K* classes gives each class about *R/K* on
average, so a class can only top the ranking if the pool can supply more than
*R/K* of it. The smallest class therefore caps the haystack at
`smallest_class × K` records. Even after cutting to the five largest classes,
that is **5,865 records ≈ 259K tokens**. Our review axis runs to 987K. guardrail
cannot reach the 500K or 1M tiers, which are the whole point of a long-context
benchmark.

**And it has no twin.** Every row is Turkish text, including the ones marked
`language=="en"` — those are translated *from* English, not English. So a twin
would have to be built from the upstream English corpora (OR-Bench, WildGuardMix,
toxic-chat) and relabelled under the same jury. That is real work, and it would
still not fix the length ceiling.

**Where it would fit.** As a third, monolingual axis testing label-space
difficulty in a non-review domain at ≤250K. Not as part of the cross-lingual
comparison.

---

## "If an LLM labels the data, why is that a problem for us?"

Short answer: **for most of our questions it is not a problem at all, and the
one place it bites is not the place people usually worry about.**

**Why it mostly does not matter.** Our ground truth is the label *as the dataset
defines it*. The question "how many records are labelled X" has an exact answer
regardless of whether a human, a star rating, or a jury of three models produced
X. The model being evaluated is being asked to reproduce a stated labelling
convention, not to be right in some absolute sense. So "we used a dataset from a
reputable lab, labelled by an LLM jury, and here is the citation" is a perfectly
defensible sentence, and reviewers accept it routinely.

**Where it does bite — three specific places.**

1. **Circularity, and this is the real one.** If the labels were produced by an
   LLM, then evaluating an LLM on reproducing them measures *agreement with
   another model*, not language understanding. Model families share blind spots.
   A Qwen-based system scored against Gemma/Qwen/GPT jury labels is partly being
   scored on how similar its training distribution is to theirs. For a thesis
   whose whole point is measuring what recursive processing does to *Turkish*,
   that confound sits exactly on the finding. **This is the argument that rules
   guardrail out of the cross-lingual comparison** — more than the skew, honestly.

2. **Asymmetric noise across the twin.** If the Turkish half is model-labelled
   and the English half is human-labelled, the two halves have different
   irreducible error, and the TR-vs-EN gap you measure is partly a gap between
   labelling procedures. Anything used for RQ4 must have matched provenance on
   both sides. This is why the primary pair uses the writer's own star rating on
   *both* halves.

3. **The accuracy ceiling on `count`.** Label noise of any origin caps what a
   perfect model can score. At the 100K tier even 2% noise caps `count` at 0.36
   under the OOLONG metric. Ranking families are immune and `proportion` is
   robust, so this is a metric-selection issue, not a data-rejection issue. Full
   table in `DATACARD.md`.

**Practical rule for this project.** LLM-labelled data is acceptable for a
**monolingual** axis where the task is explicitly "reproduce this convention".
It is not acceptable for the **cross-lingual** axis, where labelling procedure
must be identical on both sides and must not be another LLM's judgement.

---

## Recommendation

1. **Change nothing about the primary pair.** `vitamins_tr` ↔ `amazon_hpc_en`
   is sound and is the only pair with a usable entity axis.
2. **DONE (2026-08-25).** MüşteriYorumları added as a *third* Turkish review set
   alongside the existing ones rather than replacing We-Bears. It costs nothing,
   alongside the existing ones. Its twin is **MARC English**
   (`SetFit/amazon_reviews_multi_en`, Apache-2.0), not `app_reviews`: the latter
   is a closer length match but is tagged `license:unknown`, and MARC reached a
   **better** twin asymmetry anyway — **0.010, the lowest in the benchmark**.
3. **Do not adopt guardrail-tr for the cross-lingual axis**, for the circularity
   reason above and the 259K ceiling. Reconsider it only if a monolingual
   label-space-difficulty axis is wanted.
4. **~~We-Bears stays as a secondary robustness check.~~ WITHDRAWN 2026-08-30.**
   Provenance is the one defect filtering cannot fix — you cannot filter for not
   knowing where the labels came from. `top_k` was withdrawn with it, since that
   corpus was the only one where exact ordering passed prior-neutrality.


---

# The twin search

Every English corpus considered as a partner for a Turkish set, measured rather
than assumed. Target: a Turkish review set averages 12–14 words with a style lift
near zero.

## Amazon-Reviews-2023 — no category works

| category | mean words | style lift |
|---|---|---|
| Grocery_and_Gourmet_Food | 46.8 | +0.091 |
| Appliances | 52.5 | +0.099 |
| All_Beauty | 58.9 | +0.067 |
| Office_Products | 59.7 | +0.072 |
| Home_and_Kitchen | 71.8 | +0.062 |
| Baby_Products | 72.3 | +0.051 |
| Digital_Music | 79.0 | +0.091 |
| Video_Games | 85.9 | +0.083 |

3.5–6.5x too long and +0.05 to +0.10 of style signal in every one, because "long
review = negative" is universal on Amazon. Home_and_Kitchen was near the **best**
of the eight, so re-picking the category does not help.

## Parallel corpora — dead on scale, not on quality

These give a record-matched twin by construction, the strongest possible design.
Both are far too small:

- **SIB-200** (tur/eng, 7 topic classes, FLORES-parallel): **1,004 rows total**,
  ceiling ≈ 14K tokens. Cannot reach even the 50K tier.
- **XNLI** (tr/en, 3 classes): human-translated portion is **7,500 rows**, which
  one 250K haystack would consume entirely. The 392,702-row train split is
  **machine-translated**, the exact confound the morphology claim must avoid.

**This is a ceiling on the design, not a gap in the search.** Human translation
is expensive, so parallel corpora are small, and this benchmark needs a large
pool for independent draws at 100K–1M tokens. MASSIVE, at 16.5K parallel
utterances, is the largest parallel Turkish resource that exists and is already
the intent axis.

## `sealuzh/app_reviews` — the one strong hit

F-Droid app reviews (Grano et al., 2017). 288,065 rows, 14.7 mean words, style
lift +0.000, 392 apps at entity MI 0.044, reaches 750K, and **it is one of
OOLONG's own ten source datasets**. Licence unstated upstream, so text is
withheld and rebuilt locally, the same treatment `amazon_hpc_en` gets.

**Its value is not as a replacement.** Substituted into the primary pair it gives
an asymmetry of 0.021 against the current 0.015, i.e. marginally worse. Its value
is (a) as MüşteriYorumları's twin, and (b) it carries a real **`date` column**
(2014–2017), the substrate for the timeline axis TR-OOLONG lacks.

## Measured pairings, all of them

| pairing | length match | asymmetry | verdict |
|---|---|---|---|
| MASSIVE tr ↔ en | identical | **0.015** | best; true record-matched twin |
| `vitamins_tr` ↔ `amazon_hpc_en` | 12.1 vs 44.8 w | **0.017** | ships as primary review pair |
| **MüşteriYorumları ↔ MARC English** | 13.8 vs 34.1 w | **0.010** | **ships. Lowest asymmetry measured; both halves Apache-2.0 / CC-BY-SA** |
| MüşteriYorumları ↔ `app_reviews` | **13.8 vs 14.7 w** | 0.030 | best *length* match, but `license:unknown` |
| `vitamins_tr` ↔ `app_reviews` | 12.1 vs 14.7 w | 0.021 | no better than the pair in use |
| MüşteriYorumları ↔ Amazon Home | 13.8 vs 67.3 w | 0.106 | rejected |
| ~~We-Bears ↔ airline tweets~~ | 24.2 vs 15.7 w | **0.108** | **withdrawn v0.5.0** |
| SIB-200 / XNLI | identical | — | structurally dead |

---

# A swap that was built, tested, and not adopted

MüşteriYorumları was first paired with Amazon `Home_and_Kitchen`, built in full
(138 questions each, 6 families, all gates passing), specifically to test whether
replacing We-Bears would fix the cross-lingual confound.

**It did not.** Twin asymmetry came out at 0.106 against the We-Bears pair's
0.108 — unchanged.

**The lesson, which cost the most to learn.** We-Bears has a +0.120 style lift at
the **source** level against its twin's +0.017, a 7x gap. That does **not**
propagate to question-level exploitability, because prior-randomised sampling
(D9) absorbs it. The swap was proposed on the source-level number alone and the
number that mattered did not move.

**Always run a solver against the built questions, not the source pool.**

The Amazon `Home_and_Kitchen` half also turned out to carry a `most_common` style
lift of +0.250 on its own, which is how `app_reviews` was found.
