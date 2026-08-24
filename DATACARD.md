# TR-OOLONG — Datacard

Per-axis provenance, licensing, and construction. Ground truth for every question
is derived from source labels by two independent code paths (see README §5); there
is no manual answer annotation.

## Intent axis (released first)

- Source: Amazon MASSIVE, locales `tr-TR` and `en-US` (AmazonScience/massive),
  fetched by `scripts/massive.py`.
- Label: `intent` (**48** classes retained of 60). Entity: `scenario` (18) —
  nested in intent, so the four entity families are omitted; the six non-entity
  families apply (count, proportion, shift, most_common, least_common,
  second_most).
- **Class support floor.** 12 intents have fewer than 100 rows and were dropped.
  The motivating case: `cooking_query` has 6 rows in 16.5K, so it was the rarest
  label in every haystack and `least_common` was answerable from corpus priors
  alone (majority baseline 1.00 — the gold answer was `cooking_query` in 10/10
  haystacks, in *both* languages). After the cut, `least_common` has a majority
  baseline of 0.20 with 8–9 distinct answers per 10 haystacks.
  Dropped: `audio_volume_down`, `audio_volume_other`, `cooking_query`,
  `datetime_convert`, `email_addcontact`, `general_greet`, `iot_hue_lighton`,
  `iot_hue_lightdim`, `iot_wemo_off`, `iot_wemo_on`, `music_dislikeness`,
  `music_settings`.
- Cross-lingual control: TR and EN are the *same* utterances, professionally
  parallel-translated. Both the leakage filter and the support floor are applied
  as a **union over the locale pair** (drop the utterance/class from both if it
  fails in either), so the twin retains an identical label space and an identical
  source row set. Applying either filter per locale would have left TR and EN with
  different class sets — a comparison across different label spaces.
- Label leakage: 112 English utterances (0.68%) contain their intent's surface
  form; **zero** Turkish utterances do. Those 112 pairs are dropped from both
  locales. This rate is the cross-lingual leakage measurement reported in
  README §4.
- License: MASSIVE is CC-BY-4.0. Verify at release time.
- Proportion unit: per-mille (label space > 10).
- Label noise: [ ] to be measured on the 200-row self-annotation slice.

## Review / sentiment axis (built, not yet distributed)

Rests on two independent TR–EN corpus pairs, so results can be shown to hold across
datasets rather than one source. Label is `sentiment` (3 classes); the entity
(`brand` / `airline`) is orthogonal to the label, so all ten families apply.
Carries the length gradient up to 1M tokens (see README §4 for how each set's
maximum length is derived from its smallest class). Proportion unit: percent.

**Pair (a) — brand reviews / airline tweets**
- Source (TR): Turkish brand reviews (We-Bears/Turkish-Review-Sentiment-Data),
  fetched by `scripts/webears.py`.
  Twin (EN): Twitter US Airline Sentiment (CrowdFlower, Feb 2015), via
  `osanseviero/twitter-airline-sentiment`, fetched by `scripts/airline.py`.
- Labels are native 3-class sentiment.
- **Selection effect (TR).** 15,411 of 40,597 We-Bears rows (38%) carry
  comma-joined multi-aspect labels (`olumsuz,olumlu`) rather than a single
  sentiment. The builder drops them, since the benchmark's ground truth requires
  one label per record. The retained subset is therefore not a random sample of
  the corpus: it skews toward shorter, single-aspect reviews, and toward
  negative (15,637 olumsuz / 5,734 olumlu / 3,815 nötr before other filters).
  Aggregate counts are still exact with respect to the *built* haystack, which
  is what every question asks about — but the pool is not representative of
  Turkish review text in general.
- License: We-Bears is **Apache-2.0** — distributable. The airline twin is
  **CC-BY-NC-SA-4.0** — non-commercial and share-alike, so its text is withheld
  from the release and rebuilt locally. See the licensing table below.

**Pair (b) — supplement reviews (same-domain twin)**
- Source (TR): turkish-nlp-suite/vitamins-supplements-reviews (Vitaminler.com).
  Twin (EN): McAuley-Lab/Amazon-Reviews-2023, Health_and_Personal_Care subset.
- Labels derived from 1–5 star ratings by a fixed map (1–2 negative, 3 neutral,
  4–5 positive); the pool is stratified to cap per-class dominance.
- EN brand attached by joining the review shard to the metadata shard on
  `parent_asin` (`store` field = brand).
- Domain-matched twin (both supplement/health reviews), tighter than pair (a).
- License: TR set is **CC-BY-SA-4.0** — distributable, but share-alike, so this
  subset and anything derived from it must remain CC-BY-SA-4.0. EN
  Amazon-Reviews-2023 review text is governed by **Amazon's Conditions of Use**,
  not by the repository license: its text is **withheld** from the release. See
  the licensing table below.
- Label noise: [ ] to be measured.


## Licensing — verified 2026-08-24

**The six source corpora do not share a license, and two of them must not have
their text redistributed.** `scripts/publish_hf.py` enforces this: each set is
packaged as its own Hugging Face config with its own license tag, and the two
restricted sets ship as questions-and-answers only, with the haystack text
withheld and rebuilt locally from the public source.

| Set | Source | License | Redistribute text? | Obligation |
|---|---|---|---|---|
| `tr_intent`, `en_intent` (+ paired) | AmazonScience/massive | **CC-BY-4.0** | yes | attribute; state changes |
| `tr_oolong` | We-Bears/Turkish-Review-Sentiment-Data | **Apache-2.0** | yes | include license + notice of modification |
| `vitamins_tr` | turkish-nlp-suite/vitamins-supplements-reviews (Vitaminler.com) | **CC-BY-SA-4.0** | yes | **share-alike**: this subset and derivatives stay CC-BY-SA-4.0; cite Altinok (ACL 2023) |
| `en_twin` | Twitter US Airline Sentiment (CrowdFlower / Kaggle) | **CC-BY-NC-SA-4.0** | **no** | non-commercial **and** share-alike — text withheld |
| `amazon_hpc_en` | McAuley-Lab/Amazon-Reviews-2023 (Health & Personal Care) | repo MIT-style, **text governed by Amazon's Conditions of Use** | **no** | text withheld |

**No email or permission request is needed for any of these** — they are all
publicly licensed. The two restrictions are handled by construction, not by
correspondence:

- **`en_twin`** is CC-BY-NC-SA. Non-commercial is a restriction on *use*, not a
  bar to release, but combined with share-alike it would infect the whole
  release if shipped as one dataset. It ships text-free.
- **`amazon_hpc_en`** is the one genuine hazard. The Hugging Face repo's license
  covers the *packaging*; the review text remains subject to Amazon's terms,
  which do not grant redistribution. Withholding the text is the safe reading,
  and it costs nothing: the build is deterministic, so a user who runs
  `scripts/health.py` + the committed config gets byte-identical haystacks.

**Two things to do before release.** (1) The repository `LICENSE` is MIT and
covers *code only* — add a line saying so, since the data subsets carry their
own terms. (2) Re-check each source's license page at release time and record
the access date; license fields on Hugging Face do change.

> Earlier drafts of this datacard listed the We-Bears license as "pending
> clarification" and the Amazon set as "verify before shipping". Both are now
> resolved: We-Bears is Apache-2.0 (distributable), Amazon is not.

## Family availability per set

Not every family is meaningful on every source, and a family that fails the
prior-oracle gate is switched off rather than shipped. This is recorded here so
the per-set question counts are not mistaken for a bug.

| Set | Omitted | Why |
|---|---|---|
| `tr_intent`, `en_intent` (+paired) | the four entity families | `scenario` is *nested* in `intent`, so entity questions are trivial or impossible (detected automatically) |
| `en_twin` | `entity_argmax`, `top_k` | 6 airlines cannot form a prior-neutral 5-candidate set |
| `vitamins_tr` | `top_k` | exact ordering stayed prior-correlated (z=+5.5) |
| `amazon_hpc_en` | `top_k` | exact ordering stayed prior-correlated (z=+3.7) |
| `tr_oolong` | — | all ten families ship |

## Construction summary

- Recipe: concatenate labeled examples into a length-controlled haystack; the
  label never appears verbatim in the text — enforced by dropping any record
  containing any label's surface form (`drop_label_leakage`), not assumed.
- Class support: classes with fewer than `min_class_support` rows are dropped,
  because a class too small to be sampled competitively is deterministically the
  rarest in every haystack and makes `least_common` answerable from priors.
- Star-derived labels (supplement pair) use the fixed 3-class map above; other
  sources use native labels.
- Length: measured with one reference tokenizer per axis (Qwen/Qwen3-8B).
- Drift: one label is over-represented in the second half so `shift` questions
  have detectable signal; the target and a detectability flag are recorded.
- Reproducibility: single string seed; byte-identical rebuilds; full manifest.