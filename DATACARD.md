# TR-OOLONG — Datacard

Per-axis provenance, licensing, and construction. Ground truth for every question
is derived from source labels by two independent code paths (see README §5); there
is no manual answer annotation.

## Intent axis (released first)

- Source: Amazon MASSIVE, locales `tr-TR` and `en-US` (AmazonScience/massive).
- Label: `intent` (60 classes). Entity: `scenario` (18) — nested in intent, so
  only count/proportion/shift families apply on this axis.
- Cross-lingual control: TR and EN are the *same* utterances, professionally
  parallel-translated — the twin is parallel by construction.
- License: MASSIVE is CC-BY-4.0. Verify at release time.
- Proportion unit: per-mille (label space > 10).
- Label noise: [ ] to be measured on the 200-row self-annotation slice.

## Review / sentiment axis (built, not yet distributed)

- Source (TR): Turkish brand reviews (We-Bears/Turkish-Review-Sentiment-Data).
  Twin (EN): US airline sentiment tweets.
- Label: `sentiment` (3 classes). Entity: `brand` / `airline` — orthogonal to the
  label, so all seven families apply.
- Carries the length gradient (up to 500K tokens, TR).
- License: **pending clarification** for the We-Bears text. Until it clears, the
  axis ships as code + configs + manifests only; the text is not distributed.
- Proportion unit: percent (3 classes).
- Label noise: [ ] to be measured.

## Construction summary

- Recipe: concatenate labeled examples into a length-controlled haystack; the
  label never appears verbatim in the text.
- Length: measured with one reference tokenizer per axis (Qwen/Qwen3-8B).
- Drift: one label is over-represented in the second half so `shift` questions
  have detectable signal; the target and a detectability flag are recorded.
- Reproducibility: single string seed; byte-identical rebuilds; full manifest.
