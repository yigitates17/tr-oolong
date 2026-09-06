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
- Cross-lingual control: TR and EN share utterance IDs — each pair is the same
  source utterance rendered in each locale, carrying the same intent label.

  **They are translated *and localized*, not literally translated, and the
  distinction should be stated rather than glossed.** Measured over all 15,075
  pairs: digits are preserved in 100% of them and the EN/TR word-count ratio has
  a median of 1.25 (IQR 1.00–1.50), so the pairs are close. But 1.8% differ in
  length by more than 2×, and inspection shows why — culturally substituted named
  entities, e.g. TR *"r.t.e başkan"* against EN *"abdul k. a. l. a. m.
  president"*, or TR *"lütfen bana pırlantayı dinlet"* (a Turkish song) against
  EN *"please let me hear six hundred and sixty six the number of the beast"*.

  **Impact on the benchmark: none.** Every answer is derived from the *label*,
  which is identical across the pair, so the counting task and its ground truth
  are genuinely the same in both languages. **Impact on the morphology claim:
  small but real** — the measured 1.30–1.34× token ratio reflects localization as
  well as agglutination, so it is an upper bound on the pure morphology effect,
  not a clean estimate of it. Both the leakage filter and the support floor are applied
  as a **union over the locale pair** (drop the utterance/class from both if it
  fails in either), so the twin retains an identical label space and an identical
  source row set. Applying either filter per locale would have left TR and EN with
  different class sets — a comparison across different label spaces.
- Label leakage: **zero on both locales** in the shipped build
  (`label_leakage_rate: 0.0`). An earlier revision reported 112 English
  utterances (0.68%) against zero Turkish and read it as a cross-lingual finding;
  that claim is **withdrawn** — it is absent from this pool and was confounded by
  matching both locales against the English label vocabulary. See README §4.
  The filter still runs, and still applies as a union over the pair.
- License: MASSIVE is CC-BY-4.0. Verify at release time.
- Proportion unit: per-mille (label space > 10).
- **Label noise: measured 2026-09-04.** A native Turkish speaker judged a
  150-row pair-aligned slice (`scripts/make_noise_slice.py`, seed 42;
  `scripts/annotate_noise.py` for the protocol). **14 of 150 rejected → ε = 9.3%,
  95% Wilson CI [5.6%, 15.1%].** Higher than "professionally annotated" would
  suggest, and the reason matters — see the two subsections below.

## Review / sentiment axis (built, not yet distributed)

Rests on two independent TR–EN corpus pairs, so results can be shown to hold across
datasets rather than one source. A third pair (Turkish brand reviews ↔ airline
tweets) was **withdrawn in v0.5.0**: its Turkish half had undocumented label
provenance, a 3.6x length spread, and zero conflicting labels across 262
duplicate-text groups where the human-annotated English half had 17.1%. Label is `sentiment` (3 classes); the entity
(`brand` / `airline`) is orthogonal to the label, so all ten families apply.
Carries the length gradient up to 1M tokens (see README §4 for how each set's
maximum length is derived from its smallest class). Proportion unit: percent.

**Pair (a) — supplement reviews (carries the entity axis)**
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
- Label noise: [ ] rate still to be measured; both halves are author-assigned
  star ratings, which is the strongest provenance available (the person who wrote
  the text chose the label). See the per-family ceiling below.


## Family availability per set

*v0.6.0: `label_vs_label` added on all eight sets; the entity families now
require `render_entity` (D17) and are asserted at build time.*

Not every family is meaningful on every source, and a family that fails the
prior-oracle gate is switched off rather than shipped. This is recorded here so
the per-set question counts are not mistaken for a bug.

| Set | Omitted | Why |
|---|---|---|
| `tr_intent`, `en_intent` (+paired) | the four entity families | `scenario` is *nested* in `intent`, so entity questions are trivial or impossible (detected automatically) |
| `vitamins_tr` | `top_k` | exact ordering stayed prior-correlated (z=+5.5) |
| `musteri_tr`, `marc_en` | the four entity families | no product or brand column in either half; kept symmetric on purpose |
| `amazon_hpc_en` | `top_k` | exact ordering stayed prior-correlated (z=+3.7) |

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

## The measured intent-axis noise, and what it is actually made of

**Headline: ε = 9.3%, n = 150, 95% CI [5.6%, 15.1%].** Two qualifications belong
next to that number, and both lower the figure that should be used for the
English half.

**1. A second reviewer disagreed with 3 of the 14 rejections.** Checked against
how the corpus uses each label elsewhere, three look correct as assigned:

| row | utterance | label | why it stands |
|---|---|---|---|
| 78 | *what purpose the event been scheduled for* | `calendar_query` | the family covers "check when the show starts", "what is the time for jimmy's party" |
| 88 | *how many meetings have there been* | `calendar_query` | same |
| 90 | *look up the residential address of my team leader* | `email_querycontact` | the family is contact-detail lookup — "what's the email address of silvia", "tell me the landline number" |

Four are clear errors on any reading — row 122 *"tell me the nearest location"*
labelled `lists_remove` (a family otherwise entirely about deleting list items),
row 59 *"mail administrator"* labelled `email_sendemail` (a bare noun phrase with
no send action), row 43 (closing hours labelled as a recommendation) and row 14
(below). The remaining seven are genuinely ambiguous — mostly `qa_definition` vs
`qa_factoid`, and the corpus convention that *"do i need a hat"* is a
`weather_query`, which is consistent across the corpus but underdetermined in any
single utterance.

**So the defensible range is ε ∈ [2.7%, 9.3%]**, with ~7.3% the best point
estimate (14 rejections less the 3 overturned). Report the range, not the point:
inter-annotator disagreement at this rate is itself the finding.

## ⚠️ Part of the "noise" is mistranslation, and it is asymmetric

**This is the more important result of the annotation exercise.** MASSIVE is a
human *localization* of English SLURP utterances, and some labels are correct for
the English source while being wrong for the Turkish that ships:

| EN source | TR as shipped | label | what happened |
|---|---|---|---|
| *put a record on* | *bir kayıt koy* | `play_music` | the idiom is gone. Turkish `kayıt` is a record/registration in the clerical sense, never a vinyl. No Turkish reader infers "play music" |
| *how to spell the word treble* | *üç kat kelimesi nasıl kodlanır* | `qa_definition` | "treble" → "üç kat" (threefold), "spell" → "kodlanır" (is encoded) |
| *when does olive garden close today* | *hanım eli bugün ne zaman kapanıyor* | `recommendation_locations` | a US restaurant chain localized to a Turkish pastry |

**Why this matters more than the headline ε.** These are not annotation errors —
they are *translation* errors, and they land on **one half of the twin only**.
The English half's label is right; the Turkish half's is not. A Turkish model is
therefore scored against noisier ground truth than its English counterpart, on
records that are supposed to be identical.

That is a **direct confound for the cross-lingual claim**, which is the whole
point of the intent axis. At least 2 of 150 (1.3%) are unambiguously of this
kind; the true rate needs a pass that judges TR and EN separately, which the
current protocol does not do.

**Consequences, in order:**

1. **State it as a limitation of the intent axis.** The review axis is unaffected
   — `vitamins_tr` and `musteri_tr` are natively written Turkish with the
   writer's own star as the label, so there is no translation step to corrupt.
2. **The record-matched twin's headline claim survives but needs the caveat.**
   Any TR−EN gap on the intent axis is (language effect) + (translation noise),
   and the second term is not currently separated.
3. **The fix is a two-column protocol** — judge "does the label fit the English"
   and "does it fit the Turkish" as separate questions on the same rows. That
   turns the confound into a measurement, and it is the same 150 rows again.

## Label noise is a per-family ceiling, not a global one

Ground truth is the source label, so a wrong label does not make an answer wrong
with respect to the haystack. What it does is cap the score a semantically
perfect model could reach. That cap is strongly family-dependent. Under the
OOLONG metric `0.75^|y-ŷ|`, with symmetric flips at rate ε, an oracle that
classifies every record correctly by human judgement but disagrees with the
dataset label at rate ε scores:

| family | ε=2% | ε=5% | ε=10% | ε=20% |
|---|---|---|---|---|
| `count`, N=1,531 (smallest tier) | 0.46 | 0.35 | 0.27 | 0.20 |
| `count`, N=3,919 (100K tier) | 0.36 | 0.25 | 0.19 | 0.14 |
| `count`, N=9,873 (500K tier) | 0.26 | 0.18 | 0.13 | 0.09 |
| `proportion` (percent), N=3,919 | — | 0.95 | 0.92 | — |
| `most_common` / `pairwise` / `top_k` | P(answer flips) < 1e-6 at every N and ε tested | | | |

Ranking families are effectively immune: the builder enforces a 10% gold margin
while noise drift grows only as √(Nε). Normalised `proportion` is robust. Raw
`count` is not — at the 100K tier even 2% noise caps a perfect model at 0.36,
which is a second and independent reason to read `relative` rather than
`partial`. **Headline results should be reported on ranking and `proportion`.**

Measuring ε itself remains open. n = 400 per corpus gives ±3 points at ε ≈ 0.10.

## Surface shape per source

Measured by `scripts/style_solver.py` (README §4d). "Spread" is the ratio of the
longest class's mean word count to the shortest's.

| source | label provenance | length spread | mean style lift |
|---|---|---|---|
| MASSIVE tr-TR / en-US | professional annotation, parallel | — | −0.121 / −0.088 |
| `vitamins_tr` | author's own 1–5 stars | 1.5x | **+0.007** |
| `amazon_hpc_en` | author's own 1–5 stars | 1.1x | −0.008 |
| `musteri_tr` | author's own 1–5 stars | 1.2x | −0.044 |
| `marc_en` | author's own 1–5 stars | 1.1x | −0.054 |

Two notes on the brand-review set. Its 3.6x length spread is the largest of any
source here (`olumsuz` averages 33.1 words and ends in a period 48% of the time;
`olumlu` averages 9.1 words and ends in a period 99% of the time). And **0 of its
262 duplicate-text groups carry conflicting labels**, against 17.1% for the
human-annotated airline set — the signature of programmatic rather than human
labelling. **This is why the pair was withdrawn.** Its label provenance is undocumented upstream.

Neither fact invalidates the set: at question level its mean style lift is
−0.008, because prior-randomised sampling absorbs most of the source-level
signal. But the **twin asymmetry** for that pair is 0.108, against 0.015 for the
supplement pair and 0.017 for the record-matched intent pair. Source-level
shortcut measurements do not predict question-level ones, and the pair-level gap
is the figure that bears on the cross-lingual claim.

## Which pair is primary, and why

- **Primary cross-lingual review pair: `vitamins_tr` ↔ `amazon_hpc_en`.**
  Same domain, author-assigned star labels on both sides, an orthogonal entity
  axis on the Turkish half (normalised MI 0.022 after the `min_entity_examples`
  filter), and a twin asymmetry of 0.015. Its one weakness is a 3.7x record
  length mismatch.
- **Withdrawn in v0.5.0: Turkish brand reviews ↔ airline tweets.** Its Turkish
  half had undocumented label provenance and a 3.6x length spread, and the pair's
  twin asymmetry was 0.108 against 0.010–0.017 for the sets that remain. Removing
  it also removed `top_k`, which shipped on that corpus alone.
- **Strongest twin overall is the intent axis**, where TR and EN are the same
  utterances. Nothing in the review axis matches that, and nothing can: parallel
  corpora large enough for 100K–1M-token haystacks do not exist for Turkish
  beyond MASSIVE's 16.5K utterances. See `DATASET_REVIEW.md` for the full search.

## Licensing — what can be published, verified 2026-08-25

**Nothing here requires an email or a permission request.** Every source is
publicly licensed. Only one of the eight sets carries a redistribution restriction, and it is
handled by construction rather than by correspondence.

| set | source | licence | text redistributable? | obligation |
|---|---|---|---|---|
| `tr_intent`, `en_intent` (+paired) | AmazonScience/massive | **CC-BY-4.0** | yes | attribute; state changes |
| `vitamins_tr` | turkish-nlp-suite (Vitaminler.com) | **CC-BY-SA-4.0** | yes | **share-alike**; cite Altınok (ACL 2023) |
| `musteri_tr` | turkish-nlp-suite (Hepsiburada/Trendyol) | **CC-BY-SA-4.0** | yes | **share-alike** |
| `marc_en` | SetFit/amazon_reviews_multi_en | **Apache-2.0** | yes | include licence |
| `amazon_hpc_en` | McAuley-Lab/Amazon-Reviews-2023 | repo has **no licence tag**; text under Amazon's Conditions of Use | **no** | withhold text |

### The three things to be careful about

**1. Share-alike is contagious, and it now covers two Turkish sets.**
`vitamins_tr` and `musteri_tr` are CC-BY-SA-4.0. Anything derived from those
subsets — including our haystacks, since they are concatenations of the text —
must be released under CC-BY-SA-4.0. This is why the release is **packaged as one
Hugging Face config per source**, each with its own licence tag, rather than as a
single dataset: one licence field cannot describe this collection honestly, and
merging them would force the strictest terms onto everything.

**2. One set must ship without its text.** `amazon_hpc_en` is the genuine hazard:
the HF repository has **no licence tag at all**, and the review text remains
subject to Amazon's Conditions of Use, which grant no redistribution. It ships as
**questions and answers only**, with the haystack text rebuilt locally by a
deterministic script. This costs nothing, because the build is byte-identical
from the seed. (A second such set, the CC-BY-NC-SA airline corpus, was withdrawn
along with its Turkish partner in v0.5.0 — so the release no longer carries any
non-commercial clause at all, which simplifies downstream use considerably.)

**2b. The Amazon licence was checked exhaustively, 2026-08-30.** The conclusion
is unchanged but it is now evidenced rather than assumed. There is **no licence
anywhere**: no `license` tag, no `license` field in the card metadata, **no
LICENSE file among the repository's 912 files**, no terms on the dataset card,
and no terms on the project's own site (`amazon-reviews-2023.github.io`). The
card gives a citation (Hou et al., arXiv:2403.03952) and a contact address, and
nothing else. **Silence is not permission**, so withholding the text is the only
safe reading, and it remains what we do. If a definitive answer is ever wanted,
the card lists `yphou AT ucsd.edu` — but nothing in the release depends on it.

**3. Aggregate answers are facts, not derivative text.** What we distribute for
that set is a set of questions we wrote and integers computed from label counts.
Counts over a dataset are not expressive content, so the questions-and-answers
package is on solid ground even where the text is not redistributable. This
reasoning should be stated in the release, not assumed.

### One source was rejected on licence grounds

`sealuzh/app_reviews` is a closer length match to `musteri_tr` than MARC is
(14.7 against 13.8 mean words, versus MARC's 34.1) and produced a twin asymmetry
of 0.030. **It is tagged `license:unknown`**, which is a declaration that no
grant is known — not a missing field. For a benchmark intended to be downloaded,
cited and rebuilt by others, adding a second unknown-licence dependency was
judged not worth a 0.02 improvement in one metric. MARC is Apache-2.0 and its
text is redistributable, and it reached a *better* asymmetry anyway (0.010).

### Declared per source (read by `scripts/check_pair.py`)

Two config fields are declared by hand because neither is measurable from the
data, and one of them withdrew a whole pair in v0.5.0:

| set | `licence` | `label_provenance` |
|---|---|---|
| `tr_intent`, `en_intent` (+paired) | `cc-by-4.0` | `professional_annotation` |
| `vitamins_tr` | `cc-by-sa-4.0` | `author_stars` |
| `musteri_tr` | `cc-by-sa-4.0` | `author_stars` |
| `marc_en` | `apache-2.0` | `author_stars` |
| `amazon_hpc_en` | `unknown` | `author_stars` |

### Before release

1. `LICENSE` (MIT) covers **code only** — add a line saying so, since each data
   subset carries its own terms.
2. Re-check every source's licence page at release time and record the access
   date. Licence fields on Hugging Face do change.
3. Ship the per-source config split; do not flatten into one dataset.


## Could this be published tomorrow? Blockers, ranked

**Nothing legal blocks it.** Licences are resolved, the one unlicensed source
ships text-free, and the per-source config split handles share-alike.

**Two things would draw a reviewer's first question, and neither is fatal:**

1. **No model has ever been run on it.** Every difficulty claim is a chance rate
   or a solver ceiling; none is empirical. A datasets-track reviewer will ask for
   at least one frontier model and one open model across the length gradient.
   *This is the only item I would call a genuine blocker for a venue submission —
   though not for a Hugging Face release, which can precede the paper.*
2. ✅ **`--certify` has now been run at scale (2026-09-05).** README §4 states
   that n = 10–20 per family certifies nothing, and the committed audit used to be
   exactly that size. `--certify 250` now runs clean on every family of every set,
   and the one family that had been flagged and unresolved (`en_intent`
   `most_common`, prior 0.50 vs chance 0.20, p = 0.033 at n = 10) measures
   **z = +1.9, `ok`, at 152 distinct draws** — small-sample noise, as §4's own
   rule predicted. Takes ~2 minutes; re-run before release.

**Three that should be stated rather than fixed:**

3. Label noise ε unmeasured on the annotated sets. The *consequence* is bounded
   (see above) and five of eight sets have star-derived labels where classical
   noise is near zero by construction, so this is a datacard gap, not a defect.
4. No timeline axis, because no Turkish source carries dates. Name it as a
   limitation before a reviewer finds it.
5. Haystacks within a tier share 20–38% of records at the longest tiers, so
   tier-level confidence intervals need clustered errors.

**Recommended sequence:** release the dataset now with the datacard as it stands,
run the baselines, then submit the paper. The release timestamp establishes
priority and costs nothing, and item 1 is a paper blocker rather than a release
blocker.
