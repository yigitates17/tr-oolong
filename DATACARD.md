# TR-OOLONG — Datacard

Per-axis provenance, licensing, and construction. Ground truth for every question
is derived from source labels by two independent code paths (see README §5); there
is no manual answer annotation.

## Intent axis (released first)

- Source: Amazon MASSIVE, locales `tr-TR` and `en-US` (AmazonScience/massive).
- Label: `intent` (60 classes). Entity: `scenario` (18) — nested in intent, so the
  four entity families are omitted; the six non-entity families apply
  (count, proportion, shift, most_common, least_common, second_most).
- Cross-lingual control: TR and EN are the *same* utterances, professionally
  parallel-translated — the twin is parallel by construction.
- License: MASSIVE is CC-BY-4.0. Verify at release time.
- Proportion unit: per-mille (label space > 10).
- Label noise: [ ] to be measured on the 200-row self-annotation slice.

## Review / sentiment axis (built, not yet distributed)

Rests on two independent TR–EN corpus pairs, so results can be shown to hold across
datasets rather than one source. Label is `sentiment` (3 classes); the entity
(`brand` / `airline`) is orthogonal to the label, so all ten families apply.
Carries the length gradient up to 500K tokens. Proportion unit: percent.

**Pair (a) — brand reviews / airline tweets**
- Source (TR): Turkish brand reviews (We-Bears/Turkish-Review-Sentiment-Data).
  Twin (EN): US airline sentiment tweets.
- Labels are native 3-class sentiment.
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
  label never appears verbatim in the text.
- Star-derived labels (supplement pair) use the fixed 3-class map above; other
  sources use native labels.
- Length: measured with one reference tokenizer per axis (Qwen/Qwen3-8B).
- Drift: one label is over-represented in the second half so `shift` questions
  have detectable signal; the target and a detectability flag are recorded.
- Reproducibility: single string seed; byte-identical rebuilds; full manifest.