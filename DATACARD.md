# TR-OOLONG — Datacard

Per-axis provenance, licensing, and construction. Ground truth for every question
is derived from source labels by two independent code paths (see README §5); there
is no manual answer annotation.

## Intent axis (released first)

- Source: Amazon MASSIVE, locales `tr-TR` and `en-US` (AmazonScience/massive),
  fetched by `scripts/massive.py`.
- Label: `intent` (**49** classes retained of 60). Entity: `scenario` (18) —
  nested in intent, so the four entity families are omitted; the six non-entity
  families apply (count, proportion, shift, most_common, least_common,
  second_most).
- **Class support floor.** 11 intents have fewer than 100 rows and were dropped.
  The motivating case: `cooking_query` has 6 rows in 16.5K, so it was the rarest
  label in every haystack and `least_common` was answerable from corpus priors
  alone (majority baseline 1.00 — the gold answer was `cooking_query` in 10/10
  haystacks, in *both* languages). After the cut, `least_common` has a majority
  baseline of 0.20 with 8–9 distinct answers per 10 haystacks.
  Dropped: `audio_volume_down`, `audio_volume_other`, `cooking_query`,
  `datetime_convert`, `email_addcontact`, `general_greet`, `iot_hue_lighton`,
  `iot_wemo_off`, `iot_wemo_on`, `music_dislikeness`, `music_settings`.
- Cross-lingual control: TR and EN are the *same* utterances, professionally
  parallel-translated. Both the leakage filter and the support floor are applied
  as a **union over the locale pair** (drop the utterance/class from both if it
  fails in either), so the twin retains an identical label space and an identical
  source row set. Applying either filter per locale would have left TR with 48
  classes and EN with 49 — a comparison across different label spaces.
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
Carries the length gradient up to 500K tokens. Proportion unit: percent.

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
- License: **pending clarification** for the We-Bears text. Until it clears, this
  pair ships as code + configs + manifests only; text not distributed.

**Pair (b) — supplement reviews (same-domain twin)**
- Source (TR): turkish-nlp-suite/vitamins-supplements-reviews (Vitaminler.com).
  Twin (EN): McAuley-Lab/Amazon-Reviews-2023, Health_and_Personal_Care subset.
- Labels derived from 1–5 star ratings by a fixed map (1–2 negative, 3 neutral,
  4–5 positive); the pool is stratified to cap per-class dominance.
- EN brand attached by joining the review shard to the metadata shard on
  `parent_asin` (`store` field = brand).
- Domain-matched twin (both supplement/health reviews), tighter than pair (a).
- License: TR set is CC-BY-SA-4.0 (distributable). EN Amazon-Reviews-2023 is
  academic/non-commercial provenance — **verify redistribution terms before
  shipping**; until cleared, distribute the TR set and ship the EN pair as
  code + configs + manifests.
- Label noise: [ ] to be measured.

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