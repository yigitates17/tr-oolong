# TR-OOLONG — Datacard

Per-axis provenance, licensing, and construction. Ground truth for every question
is derived from source labels by two independent code paths (see README §5); there
is no manual answer annotation.

**Covers v0.7.1: 11 subsets · 195 haystacks · 2,240 questions · 9 families ·
2 languages (1,515 tr / 725 en).** v0.7.0 was published to Hugging Face
2026-09-16. v0.7.1 is that release plus namespaced row ids (`uid`, `dataset`,
`haystack_uid`) and changes nothing else: every question, answer, haystack and
difficulty grade is byte-identical. See D22 and the id warning below.

| axis | sets | questions | very hard |
|---|---|---:|---:|
| Intent (parallel TR/EN) | `tr_intent`, `en_intent`, `tr_intent_paired`, `en_intent_paired` | 480 | 45 |
| Review / sentiment | `vitamins_tr` ↔ `amazon_hpc_en`, `musteri_tr` ↔ `marc_en` | 920 | 46 |
| Large label space (TR only, new in v0.7.0) | `sikayet_tr`, `interpress_tr`, `sinema_tr` | 840 | **168** |

⚠️ **Do not quote 2,240 as a difficulty figure.** 71.8% of the questions are
answerable by a reader that sees 5% of the records; **259** are graded very hard.
Report the easy and very-hard bands separately and report the gap between them.
The sampling section below is the one part of this document to read before
citing any number from it.

## Intent axis (released first)

- Source: Amazon MASSIVE, locales `tr-TR` and `en-US` (AmazonScience/massive),
  fetched by `scripts/massive.py`.
- Label: `intent` (**48** classes retained of 60). Entity: `scenario` (18) —
  nested in intent, so the four entity families are omitted; the six non-entity
  families apply (count, proportion, most_common, least_common, second_most,
  label_vs_label). A seventh, `shift`, was **withdrawn in v0.7.0** and is present
  only in the v0.6.3 data, which is no longer the published revision.
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
  small but real** — the measured 1.30–1.34× token ratio **under Qwen3-8B**
  reflects localization as well as agglutination, so it is an upper bound on the
  pure morphology effect, not a clean estimate of it, and it is also specific to
  that tokenizer (see PAPER_NOTES.md §1: the same aligned text runs 0.57×–2.16×
  depending on which tokenizer counts it). Both the leakage filter and the support floor are applied
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
- **Does not ship**, but exists as a measured experiment: `label_translation`
  translates the 48 intent codes to Turkish (`play_music`→`müzik_çal`), and
  leakage against the *translated* label reappears — 3.13% for the natural
  imperative form, 0.14% for the infinitive form. Configs live in
  `configs/experimental/`, deliberately outside the glob every release script
  uses, so they cannot be swept into a release by accident. See
  `DESIGN_DECISIONS.md` D19/D19b for the full measurement.
- License: MASSIVE is CC-BY-4.0. Verify at release time.
- Proportion unit: per-mille (label space > 10).
- **Label noise: measured 2026-09-04.** A native Turkish speaker judged a
  150-row pair-aligned slice (`scripts/make_noise_slice.py`, seed 42;
  `scripts/annotate_noise.py` for the protocol). **14 of 150 rejected → ε = 9.3%,
  95% Wilson CI [5.6%, 15.1%].** Higher than "professionally annotated" would
  suggest, and the reason matters — see the two subsections below.

## Review / sentiment axis (published in v0.7.0)

Rests on two independent TR–EN corpus pairs, so results can be shown to hold across
datasets rather than one source. A third pair (Turkish brand reviews ↔ airline
tweets) was **withdrawn in v0.5.0**: its Turkish half had undocumented label
provenance, a 3.6x length spread, and zero conflicting labels across 262
duplicate-text groups where the human-annotated English half had 17.1%.

Label is `sentiment` (3 classes) on both surviving pairs. Pair (a) carries an
entity column (`brand`) orthogonal to the label, so the four entity families
apply there; pair (b) has none and is kept deliberately symmetric without them.
Carries the length gradient up to 1M tokens (see README §4 for how each set's
maximum length is derived from its smallest class). Proportion unit: percent.

⚠️ **Three classes is this axis's defining weakness, and v0.7.0 is the response.**
A reader classifying a random 5% of the records and scaling up scores 0.88–0.91
on these sets' counts. That is arithmetic, not a question-design defect: the
relative error of a scaled-up sample is `sqrt((1-f)/(f*m))` in the gold magnitude
`m`, and with N records over K classes the average count is `N/K`, so resistance
needs a **large K**. See the large-label-space axis below, which exists for this
reason, and `DESIGN_DECISIONS.md` D21b.

**Pair (a) — supplement reviews (carries the entity axis)**
- Source (TR): turkish-nlp-suite/vitamins-supplements-reviews (Vitaminler.com).
  Twin (EN): McAuley-Lab/Amazon-Reviews-2023, Health_and_Personal_Care subset.
- Labels derived from 1–5 star ratings by a fixed map (1–2 negative, 3 neutral,
  4–5 positive); the pool is stratified to cap per-class dominance.
- EN brand attached by joining the review shard to the metadata shard on
  `parent_asin` (`store` field = brand).
- Domain-matched twin: both halves are supplement/health reviews.
- License: TR set is **CC-BY-SA-4.0** — distributable, but share-alike, so this
  subset and anything derived from it must remain CC-BY-SA-4.0. EN
  Amazon-Reviews-2023 review text is governed by **Amazon's Conditions of Use**,
  not by the repository license: its text is **withheld** from the release. See
  the licensing table below.
- Label noise: [ ] rate still to be measured; both halves are author-assigned
  star ratings, which is the strongest provenance available (the person who wrote
  the text chose the label). See the per-family ceiling below.

**Pair (b) — general product reviews (added v0.5.0; the cleanest pair, no entity axis)**
- Source (TR): turkish-nlp-suite/MusteriYorumlari (Hepsiburada / Trendyol).
  Twin (EN): SetFit/amazon_reviews_multi_en (MARC English).
- Same 1–5 star map as pair (a); both halves are the writer's own rating.
- **No product or brand column exists in either half**, so the four entity
  families are omitted from both — a symmetry choice, not a data failure.
- Both halves are redistributable (CC-BY-SA-4.0 and Apache-2.0), the only pair
  in the benchmark where that is true. Twin asymmetry **0.010**, the lowest here.
- ⚠️ **This pair is the classification control, not difficulty evidence.**
  `musteri_tr` contributes **0** very-hard questions and `marc_en` **1**. It
  exists to support the cross-lingual comparison and must never be cited as
  evidence that the benchmark requires aggregation.
- `sealuzh/app_reviews` was a closer length match for the English half and was
  **rejected on licence grounds**; see below.

## Large-label-space axis (added v0.7.0, Turkish only)

**Why it exists.** Everything above is 3-class or is capped at 16.5K parallel
utterances. Neither can host a small gold answer at 500K–1M tokens, which by the
arithmetic in the box above is the only property that resists a sampling reader.
These three sources were added on 2026-09-16 to supply a large K in Turkish, and
they now carry **168 of the benchmark's 259 very-hard questions**. All three are
Turkish-only: none has an English twin, so none of them bears on the
cross-lingual claim, and they must not be used for it.

⚠️ **Two of the three cannot redistribute their text** and both have an open
licence enquiry. See the licensing section; this is the biggest unresolved item
in the release.

**`sikayet_tr` — TC32 consumer complaints (29 classes, 300 questions)**
- Source: Kaggle `savasy/multiclass-classification-data-for-turkish-tc32`, file
  `ticaret-yorum.csv`. Kaggle needs an account, so `scripts/sikayet_tr.py` does
  **not** download: pass it the path to your own copy.
- 431,306 rows, 32 categories, 12,024–14,009 rows each, so near-balanced before
  anything here touches it. 280,193 rows survive cleaning.
- Label: the product category the complainant chose when filing. Slugs are
  rewritten into natural Turkish (`beyaz-esya` → *beyaz eşya*), both because the
  templates put them in front of a Turkish reader (D12) and because the
  word-level leak filter needs real words to match.
- **The file's structure is not what its header says**, and a native reader
  spotted it before the code did. The header is `category,text`, but `text` is
  really `"<TITLE>,<BODY>"` — a complaint headline joined to the narrative by a
  comma, splitting cleanly on the first comma in 100% of rows. The title is what
  names the company, so it is kept **out** of the record text.
- **Two artifacts that would have shipped unnoticed.** 89.7% of bodies end in
  *"Devamını oku"* ("read more"), a scraping truncation marker, and the 10.3%
  without it are systematically the shorter complaints — a surface feature
  correlated with length and therefore possibly with category. Stripped.
  And category-name leakage is severe for a few classes, measured body-only:
  `kargo-nakliyat` **84.7%**, `cep-telefon-kategori` **73.4%**, `anne-bebek`
  **36.9%**, every other class at or under 30%, mean 10.8%. **Those three classes
  are dropped**, leaving 29.
- ⚠️ The residual is caught by the builder's filter **only because that filter was
  hardened for this source**. `leak_surface_forms` previously matched the whole
  label string, and no Turkish complaint contains the literal `"kargo-nakliyat"`,
  so it would have reported zero leakage and passed by construction. The config
  sets `leak_label_words: true`. **Never ship this source with that flag off.**
  Even so, 24.6% of rows are dropped for label leakage.
- Licence: **none declared**, text scraped from a third-party site. Text withheld,
  enquiry open.

**`interpress_tr` — dated Turkish news (16 classes shipped, 300 questions)**
- Source: the Interpress 270k news archive. The Hugging Face repository
  `yavuzkomecoglu/interpress_news_category_tr` contains **only a loading script**
  that no current `datasets` version will run, so `scripts/interpress_tr.py`
  fetches the archive that script points at and verifies its sha256.
- 218,839 usable rows, 17 categories, **daily publication dates from 2010-11-02
  to 2017-11-01** (2,457 distinct days). 97,835 rows survive cleaning; `savunma`
  falls below the 1,000-row support floor, leaving **16** classes in the built
  label space against 17 in the source.
- Label: the publisher's own editorial section.
- Records are full news articles (median 1,650 characters), so a 100K-token
  document holds ~206 of them rather than ~1,500. Every one must still be
  classified to answer "how many are `saglik`", which is what keeps the answers
  small without turning the question into retrieval. Using `Title` instead was
  measured and is much worse: 28-character records give ~12,000 per document and
  a 5%-sample score of 0.86.
- **It is the only source here with a real length gradient.** Predicted
  5%-sample score rises 0.00 → 0.33 → 0.52 → 0.66 across the 100K/250K/500K/1M
  tiers, against 0.88–0.91 flat on the review sets.
- ⚠️ **35.1% of rows are dropped for label leakage**, by far the highest rate in
  the benchmark (`sikayet_tr` 24.6%, `sinema_tr` 0.3%, MASSIVE 0.0%). News prose
  about a section routinely names that section. The filter is doing its job, but
  the survivors are a heavily selected subset of the corpus and any claim about
  "Turkish news" from this set should say so.
- ⚠️ **It carries per-record dates, and they are deliberately unused.** The
  fetch script keeps a `date` column and the builder ignores it. This is the one
  source that could support a dated timeline family, and that family is not
  built. See the blockers section.
- Licence: card declares none. The Apache-2.0 header on the loading script covers
  the **script**, not the data. Text withheld, enquiry open.

**`sinema_tr` — BuyukSinema film reviews (10 classes, 240 questions)**
- Source: `turkish-nlp-suite/BuyukSinema`, revision `137d0ff7`. 67,328 reviews,
  text median 201 characters; 51,171 rows survive cleaning.
- Label: **the reviewer's own 10-point rating**, stored zero-indexed, rendered in
  Turkish as *"1 yıldız"* … *"10 yıldız"* rather than collapsed to sentiment
  words — collapsing a 10-point scale to 3 classes is exactly what makes the
  review sets partially readable.
- Same label provenance as `vitamins_tr` and `musteri_tr` (the writer chose the
  score) and the closest register match to them, which is why it is the natural
  strengthening of that axis rather than a separate one.
- The rating distribution is naturally uneven, from **2.4%** at *3 yıldız* up to
  **24.4%** at *8 yıldız*. That is what a rating scale looks like, and it is
  useful here: uneven classes put some counts in the rare band with no
  construction trick.
- **It is the only large-K Turkish source found with a declared licence**
  (CC-BY-SA-4.0), so it is the only one of the three that ships its text. That
  makes it matter out of proportion to its size: if both open enquiries come back
  no, it is the only redistributable large-K evidence the benchmark has.
- Share-alike applies, as for the other two turkish-nlp-suite sets.
- Shortest of the three: tiers stop at 500K, not 1M.


## Family availability per set

**Nine families ship in v0.7.0**: `count` (including rare-label counts),
`proportion`, `most_common`, `least_common`, `second_most`, `label_vs_label`,
`entity_count`, `entity_argmax`, `pairwise`. Two former families are gone and
neither is in the published data — `top_k` went with the brand-review pair in
v0.5.0, since it shipped on that corpus alone, and `shift` was **withdrawn in
v0.7.0** (see the sampling section). Neither should appear in a results table.

*v0.6.0: `label_vs_label` added on every set; the entity families now
require `render_entity` (D17) and are asserted at build time.*

Not every family is meaningful on every source, and a family that fails the
prior-oracle gate is switched off rather than shipped. This is recorded here so
the per-set question counts are not mistaken for a bug.

| Set | Omitted | Why |
|---|---|---|
| `tr_intent`, `en_intent` (+paired) | the four entity families | `scenario` is *nested* in `intent`, so entity questions are trivial or impossible (detected automatically) |
| `musteri_tr`, `marc_en` | the four entity families | no product or brand column in either half; kept symmetric on purpose |
| `sikayet_tr` | the four entity families | no column orthogonal to the category; the complaint title, which names the company, is deliberately not in the record text |
| `interpress_tr` | the four entity families, **plus `most_common`, `least_common`, `second_most`** | no orthogonal entity column. The three ranking families are switched off in config: on a 16-class news axis the section shares are close enough that the `min_rank_margin` floor (0.15) rejects nearly every draw |
| `sinema_tr` | the four entity families, **plus `most_common`, `least_common`, `second_most`** | no orthogonal entity column. The ranking families are **not** disabled in config here — the builder emitted none, because adjacent points on a 10-point rating scale rarely clear the 0.15 margin. This is the starvation case the builder is built to report loudly rather than absorb silently |

**Read the last two rows together with the question counts.** `interpress_tr`
and `sinema_tr` ship only three kinds each (`count`, `proportion`,
`label_vs_label`), which is why their 300 and 240 questions are not distributed
like the other sets'. It is the intended outcome of the difficulty floors, not a
build failure.

### ⚠️ The entity families are LENGTH-GATED. Do not read them as available at every tier.

`min_entity_examples` is an absolute record count, while the number of entities
clearing it scales with haystack size. Short haystacks therefore cannot form a
prior-neutral candidate set, and the builder correctly declines to emit the
question rather than shipping one decided by a one-record margin. Measured on
the shipped build:

| tier | `vitamins_tr` (count / argmax / pairwise) | `amazon_hpc_en` |
|---|---|---|
| 100K | 5 / **0** / 5 | 4 / **0** / **0** |
| 250K | 5 / 2 / 5 | 5 / **0** / 5 |
| 500K | 5 / 5 / 5 | 5 / 3 / 5 |
| 750K / 1M | 5 / 5 / 5 | 5 / 5 / 5 |

**Two consequences for anyone using this dataset.** `entity_argmax` is
effectively a 500K-and-above family on both halves. And **at the 100K tier the
two halves are not comparable on `pairwise`** — Turkish emits five questions,
English none — because `amazon_hpc_en` averages ~1.4 reviews per brand at that
length (1,146 brands over 1,622 records) against ~15.6 for `vitamins_tr`.

Any accuracy-versus-length analysis must state which families exist at which
tier. The build prints this per tier (`[family availability]`).

**Related, measured the same day:** how often a review names a brand *other*
than the one it is filed under — `vitamins_tr` **0.66%**, `amazon_hpc_en`
**13.8%**. The English figure is inflated by brand names that are ordinary
words, so treat it as an upper bound pending a common-word filter. It does not
affect correctness either way: the grouping key is the rendered `[[entity]]`
marker and the metadata column, never free-text mentions.

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
- Drift: one label is over-represented in the second half; the target and a
  detectability flag are recorded. This existed so `shift` questions had
  detectable signal. `shift` is withdrawn in v0.7.0 but the drift is kept,
  because it is what stops the document being fully exchangeable.
- Reproducibility: single string seed; byte-identical rebuilds; full manifest.
- Row identity: `uid` (`<dataset>:<id>`) is globally unique; `id` is unique only
  *within* a subset. **Pool on `uid`.** See the warning below.

### ⚠️ `id` is not unique across subsets. Key on `uid`.

`id` is minted per subset as `<tier>-<n>-q<i>`, so `tr-100000-0-q0` is a
different question with a different answer in each of the six Turkish subsets
built at that tier: answer 13 in `interpress_tr`, 31 in `sinema_tr`, 14 in
`sikayet_tr`. Across the benchmark the 2,240 questions carry only **955**
distinct `id` values and the 195 haystacks only **80**.

Concatenating the subsets and keying on `id` therefore drops **57%** of the
benchmark silently, with no error. v0.7.1 adds `uid`, `dataset` and
`haystack_uid` for this reason and keeps `id` unchanged.
`scripts/verify_release.py` now enforces global uniqueness.

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

## ⚠️ Sampling exposure — measured 2026-09-15, and it bounds what this benchmark demonstrates

**Read this before quoting the benchmark as requiring a model to process every
record.** A fifth acceptance solver (`scripts/sampling_solver.py`) tests whether
a question can be answered by reading only a *fraction* of the haystack:
sample records at random, compute the answer on the sample, scale back up. The
other four solvers are structurally blind to this, because none of them samples.

**It works, and on most families it works very well.** Four readers are
modelled, all spending the **same** budget of k records and differing only in
where those records come from: `random` (uniformly at random), `prefix` (the
first k), `headtail` (k/2 at the start and k/2 at the end) and `stride` (k
evenly spaced end to end). Scores are `relative`; every partial reader is handed
the true label of each record it reads, so these are upper bounds:

| set | family | ref | rnd 5% | rnd 25% | pfx 5% | pfx 25% | **ht 5%** | **ht 25%** |
|---|---|---|---|---|---|---|---|---|
| `vitamins_tr` | `count` | 0.62 | 0.92 | 0.97 | 0.65 | 0.69 | **0.91** | **0.98** |
| `musteri_tr` | `count` | 0.55 | 0.89 | 0.96 | 0.66 | 0.70 | **0.91** | **0.97** |
| `amazon_hpc_en` | `count` | 0.43 | 0.89 | 0.96 | 0.70 | 0.71 | **0.90** | **0.95** |
| `musteri_tr` | `most_common` | 0.55 | 0.98 | 0.99 | 0.82 | 0.82 | **1.00** | **1.00** |
| `tr_intent` | `most_common` | 0.10 | 0.45 | 0.80 | 0.50 | 0.70 | 0.30 | **0.90** |
| `tr_intent_paired` | `count` | 0.47 | 0.54 | 0.81 | 0.55 | 0.81 | 0.56 | 0.79 |
| `tr_intent_paired` | `label_vs_label` | 0.50 | 0.49 | 0.55 | 0.60 | 0.50 | 0.60 | 0.50 |
| `vitamins_tr` | `entity_count` | 0.20 | 0.38 | 0.74 | 0.42 | 0.51 | 0.48 | 0.74 |

**`headtail` and `stride` were added on 2026-09-16 and they are the honest
readers.** Before that only `random` and `prefix` were modelled. The haystack is
two internally-shuffled blocks split at the midpoint, so every label except the
drift target is exchangeable across the whole document. `prefix` is the only
cheap reader that document order biases; `headtail` costs exactly the same and
beats it on every numeric row above. Read the `ht` columns when the question is
how much a cheap reader can get.

**`blind` is the reference, not the majority baseline, and this corrects the
first version of this section.** The majority baseline (0.02–0.05 on `count`)
is exact-match answer frequency. Under `relative`, a reader that opens nothing,
counts the separators and answers N/3 already scores 0.43–0.63 on `count` and
`proportion`. Every numeric score must be read as lift over that floor.
`quality_audit.py` now prints it (`blind`) beside the corpus-prior guess scored
the same way (`p.rel`); its exact-match prior gate had passed the numeric
families by construction.

**Under `relative`, the length axis is flat.** A fixed budget of 1,000 randomly
read records scores 0.94–0.97 on `count` at every tier from 100K to 1M on all
four review sets, because a proportion's standard error depends on how many
records were read, not on how many exist.

An earlier version of this section added that a 1,000-record *prefix* reader
"degrades only mildly (0.88 to 0.53 on `amazon_hpc_en`)" and attributed that
decay to the injected drift. **That attribution was wrong.** On the same
1,000-record budget the `headtail` reader is flat across tiers (0.97 at 100K to
0.92 at 1M on `amazon_hpc_en`), so the prefix decay is neither a length effect
nor evidence that the drift resists partial reading. It is the one reader whose
window sits entirely inside a single block, and splitting the identical budget
between the two ends removes it. Do not cite the prefix column as evidence that
truncation is costly without the headtail column beside it.

On the numeric families (64% of the questions) a `relative` score therefore
cannot distinguish a model that read 1,000 records from one that read 16,000.
What the length axis still tests is whether a model survives ingestion at all.

**`shift` is withdrawn in v0.7.0 because a two-window reader solves it.**
`shift` asked whether a label's share rose or fell between the first and second
half. A `headtail` reader classifying fifty records at each end of a
16,000-record document scores **1.000 on all eight sets that then existed, at a
25% budget** and 0.90 to 1.00 at 5%, against a majority baseline of 0.50 to 0.70.
The haystack is two blocks split at the midpoint, so the answer is a step
function at a known position and its direction is one bit; two windows at the
extremes read it off directly. Widening the drift or smoothing it into a gradient
does not help, because direction is the whole question. The family is disabled in
every config as of v0.7.0. **It is absent from the v0.7.0 release: no
`shift` question ships in any of the eleven subsets.** It was present in the
v0.6.3 data, which was the published revision until 16 September; **a v0.6.3
result on `shift` should be discarded rather than caveated.** Rationale:
`DESIGN_DECISIONS.md` D20, README section 4e-i.

**Every question now carries a measured difficulty grade, and it changes how a
score must be reported.** Each of the 2,240 questions was run against all four
partial readers at a 5% budget; the grade comes from the best score any reader
achieved on that question alone.

| grade | questions | share | what it measures |
|---|---:|---:|---|
| **very hard** (< 0.35) | 259 | 11.6% | whether the model aggregated over the whole document |
| hard (0.35–0.60) | 140 | 6.2% | |
| moderate (0.60–0.80) | 232 | 10.4% | |
| **easy** (≥ 0.80) | 1,609 | **71.8%** | whether the model can classify Turkish records at all |

**The 5% budget is a reporting choice, not a tuned one, and the whole curve is
measured.** Every question was regraded at six budgets (200 random draws each,
deterministic readers once):

| budget | very hard | hard | moderate | easy |
|---|---:|---:|---:|---:|
| 1% | 771 (34.4%) | 117 | 133 | 1,219 |
| 2% | 584 (26.1%) | 122 | 166 | 1,368 |
| **5% (shipped)** | **259 (11.6%)** | **140** | **232** | **1,609** |
| 10% | 105 (4.7%) | 103 | 222 | 1,810 |
| 25% | 38 (1.7%) | 34 | 142 | 2,026 |
| 50% | 28 (1.2%) | 2 | 38 | 2,172 |

The decline is smooth: there is no threshold at which the benchmark becomes hard
or easy, so no budget was chosen to make a point. 5% is the **conservative** end
of the plausible range (1% would let the benchmark claim 771 very-hard questions
instead of 259), and **28 questions resist even a reader that sees half the
document**.

**A fifth reader moves 28 of the hardest questions, as predicted.** A solver that
greps the category name and its component words, ASCII-folded, was run as a fifth
strategy. Of the 215 very-hard questions it can attempt, **28 leave the band**,
concentrated in `interpress_tr` and `sikayet_tr` where a category name
(`iletişim`, `sağlık`) is an ordinary Turkish word that appears in articles filed
under it. The four sets that ship text unmodified are unaffected. This is the
declared limitation of grading against a fixed reader set, now measured rather
than asserted.

**337 questions ask the same fact twice.** For 337 (haystack, label) pairs the
benchmark asks both `count` and `proportion`. Deriving the count from its
proportion twin (`count = proportion × N / unit`) scores **0.972** mean
`relative`, and succeeds at ≥0.80 for **16 questions graded very hard**. This is
harmless for one-question-at-a-time evaluation, but (a) a harness that puts all
of a haystack's questions in one prompt hands the model a shortcut, and (b)
**2,240 questions are not 2,240 independent observations**: 674 of them cover 337
facts. Use the smaller figure in any power calculation.

**Report the two bands separately and report the gap. Never pool all 2,240 into
one number.** The gap between a model's `easy` score and its `very hard` score is
an estimate of how much of the document it read, which is the attribution a
single score cannot make (see the paragraph below). A model at 0.90 easy and 0.30
very-hard is sampling; a model at 0.40 on both cannot classify Turkish and its
long-context result is uninterpretable.

Grades are averaged over 200 samples, worst standard error **0.035**, and the
**10.7%** of questions within two standard errors of a band boundary carry
`borderline: true`. They are relative to these four readers, which are handed the
true label of every record they read and are therefore upper bounds. **`musteri_tr`
has 0 very-hard questions and `marc_en` has 1**; those two sets are the matched
Turkish/English comparison and the classification control, never evidence of
aggregation difficulty. Files: `<set>/difficulty.jsonl`, `manifests/difficulty.json`,
method in README §4f.

**A single score cannot attribute credit between reading and classifying.** A
perfect classifier reading a random 5% (0.89–0.92 on `count`) outscores a
classifier that reads every record at 90% accuracy (0.74–0.90) and at 70%
(0.57–0.79; symmetric confusion). The ranking families are immune to classifier
noise (1.00 at 70% on every 3-class set) *and* sampling-solvable. Full grid:
`fullread_by_accuracy` in `manifests/sampling_audit.json`.

**Corpus priors leak back in where one haystack consumes too much of the pool,
and in v0.7.0 the exposed set is a different one from what earlier revisions of
this datacard named.** Under `relative`, the corpus-share oracle rises as the
per-haystack Dirichlet prior stops being realisable. Current picture, from
`manifests/quality_audit.json`:

- **`en_intent` `proportion` is the one flagged tier: 0.73 at 100K**, against
  0.36 at 50K. It is the only family on any set over the 0.70 watch threshold.
  Treat it as prior-exposed and say so wherever it is scored.
- ⚠️ **`vitamins_tr` is no longer the exposure case, and the old sentence must
  not be reused.** It reported 0.75 on `count` at the **750K tier**, and that
  tier is not in v0.7.0: the manifest records it as dropped
  (`tiers_dropped_over_pool_cap: [{tier: 750000, reason: drop_tiers}]`). The set
  now tops out at 500K and its worst prior there is **0.617** on `count`. The
  claim described data that no longer ships.
- `vitamins_tr`'s 500K tier *is* built over the 0.35 pool cap, at a pool fraction
  of **0.3774**, and the builder flags rather than drops it — blanket-thresholding
  a proxy is what dropped six tiers unnecessarily once before. That is the tier
  to watch on this set.
- Every other set peaks at or below **0.55** across all families and tiers.

**Where resistance comes from: answer magnitude, not margin width.**
`entity_count`, whose answers are small, is the most resistant shipped family
(0.24–0.35 at 5%). Unshipped `count` questions about intent labels holding 5–30
records score 0.29 at 5% and 0.64 at 25%, against 0.55 and 0.80 for the counts
that ship; the `min_answer_count` floor currently rejects them. On the
label-ranking families the mechanism is margin width: a median rank-1/rank-2
gap of 38–48% on the 3-class sets against a 10% floor, and 14% on the 48-class
axis, which is why the intent axis resists better. `label_vs_label` resists
only where its 2% "equal" dead band fires, i.e. on the intent axis (D18).

**Three qualifications, all of which matter:**

1. **Upper bounds, not model results.** The solvers are handed the true label
   of every record they read. A real model must still classify what it reads.
2. **Specific to the `relative` metric.** Under `exact`, a sampled count of
   1,712 against a gold of 1,600 scores zero. The families where `relative` and
   `exact` coincide, all the ranking families, are genuinely exposed.
3. **A consequence of scale.** A benchmark whose gold answers are single digits
   cannot be sampled; one whose answers run to thousands can be.

**What this does and does not mean.** Ground truth is unaffected: every answer
is exactly correct with respect to its haystack. What is bounded is the
*claim*: this benchmark demonstrably requires classifying Turkish records and
aggregating them, but it does **not** demonstrably require reading all of them,
and under `relative` it does not demonstrate that longer documents are harder.
Statements that a model "must process every record" should be withdrawn. Any
reported score must name its reading protocol (single prompt or agentic; tools
or none; sampling permitted or not) and be given as lift over `blind`.

**The fix, for a future version, is staged as v0.7 in `ROADMAP.md`:** a
rare-label `count` family whose answers are small enough to resist sampling,
and a cap on the pool fraction one haystack may consume so the top tier stays
prior-neutral. A margin band (reject too-wide gaps as well as too-narrow) is
kept as a weaker third option: it helps the ranking families only and cannot
touch `count`/`proportion`. Not applied in this release.

## ⚠️ Label noise hits RARE-label counts hardest, and those are the hard questions

**Measured 2026-09-20 by simulation on the shipped haystacks** (symmetric flips
at rate ε, `relative` metric, gold recomputed from the flipped labels):

| set | ε | ordinary `count` | **rare `count`** |
|---|---:|---:|---:|
| `tr_intent` | 7.3% | 0.930 | **0.651** |
| `tr_intent` | 9.3% | 0.905 | **0.534** |
| `sikayet_tr` | 7.3% | 0.858 | **0.463** |
| `sikayet_tr` | 9.3% | 0.832 | **0.390** |
| `interpress_tr` | 9.3% | 0.889 | **0.571** |

**Why the gap: strays flow IN at a rate that does not depend on class size.**
For a class of size C in a document of N records over K classes, symmetric noise
takes **ε·C out** (proportional to C) and brings **ε·(N−C)/(K−1) in** (roughly
constant across classes). Simulated at ε=9%, N=2,449, K=29, 300 trials:

| class | true | observed | error |
|---|---:|---:|---:|
| large (`otomotiv`) | 800 | 733 | **−8%** |
| small (`elektronik`) | 6 | 13.1 | **+119%** |

Every class receives about **7.9** strays, large or small. For a class of 800
that is negligible against the 72 it loses. For a class of 6 it is larger than
the class itself, and the count more than doubles. **Relative damage scales as
1/C**, so the smaller the true answer, the worse the corruption.

**The tension this creates, stated plainly.** Rare-label counts exist because
they are the only family a partial reader cannot estimate (D21). They are
therefore also the family a mislabelled corpus damages most. The very-hard
subset carries a noise ceiling that the easy subset does not.

### The ceiling is already measured, and "label noise" is the wrong name for it

**On these two sets, a "wrong" label is not well defined, and that is the point.**
`sikayet_tr`'s category is **chosen by the complainant when filing**, and
`interpress_tr`'s is the **publisher's own editorial desk**. Neither is an
annotator's judgement about content, so neither can be "wrong": both record a
real fact. What varies is how well that fact is **recoverable from the text**.

**So the quantity that bounds the benchmark is label PREDICTABILITY, not label
error, and `sampling_solver.py` already reports it** as `fullread@acc`: a reader
that opens **every** record but classifies each one correctly only with
probability `a`.

| set | family | full read @ 70% | full read @ 90% | blind |
|---|---|---:|---:|---:|
| `sikayet_tr` | `count` | 0.642 | 0.817 | 0.351 |
| `sikayet_tr` | **`count_rare`** | **0.155** | **0.381** | 0.044 |
| `interpress_tr` | `count` | 0.700 | 0.863 | 0.436 |
| `interpress_tr` | **`count_rare`** | **0.368** | **0.576** | 0.183 |
| `tr_intent` | **`count_rare`** | **0.182** | **0.528** | 0.000 |

**Read the `count_rare` rows carefully: they are the benchmark's real ceiling.**
A model that reads every single record and is right 90% of the time scores
**0.381** on `sikayet_tr`'s rare counts, barely above the 0.35 `very hard`
boundary. This is not a defect of the corpus and no amount of relabelling
removes it: it is the 1/C amplification above, applied to a model's own errors
instead of the corpus's.

**Consequences.** (1) Report `count_rare` results against `fullread@0.9`, not
against 1.0, or the family looks impossible when it is merely demanding. (2) An
independent measurement of how far the source labels themselves sit from a
Turkish reader's judgement is still worth having, and a 200-row slice is
generated for every set (`<set>/label_noise_slice.csv`). It refines the story;
it does not gate publication, because the ceiling above already bounds what can
be claimed. (3) The intent axis's measured 7.3–9.3% is **not** transferable to
these corpora: different sources, different labelling processes.

`sinema_tr`, `vitamins_tr`, `musteri_tr`, `marc_en` and `amazon_hpc_en` are
`author_stars` (the writer's own rating), so they have no annotation step and
this concern is structurally much smaller for them.

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
| `most_common` / `pairwise` (and the other ranking families) | P(answer flips) < 1e-6 at every N and ε tested | | | |

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
| `sikayet_tr` | complainant's own category | — | **−0.094** |
| `interpress_tr` | publisher's section | — | **−0.124** |
| `sinema_tr` | author's own 10-point rating | — | **−0.164** |

**All eleven sets pass gate (d)**: no set exceeds +0.15 mean lift over majority,
and every set is in fact *negative*, i.e. the format solver does worse than
guessing the majority answer. Per-family figures for the three v0.7.0 sets:

| set | family | solver | majority | lift |
|---|---|---:|---:|---:|
| `sikayet_tr` | `count` | 0.000 | 0.067 | −0.067 |
| `sikayet_tr` | `proportion` | 0.000 | 0.100 | −0.100 |
| `sikayet_tr` | `label_vs_label` | 0.320 | 0.400 | −0.080 |
| `sikayet_tr` | `most_common` | 0.040 | 0.200 | −0.160 |
| `sikayet_tr` | `least_common` / `second_most` | 0.040 | 0.120 | −0.080 |
| `interpress_tr` | `count` | 0.000 | 0.056 | −0.056 |
| `interpress_tr` | `proportion` | 0.000 | 0.051 | −0.051 |
| `interpress_tr` | `label_vs_label` | 0.241 | 0.506 | −0.265 |
| `sinema_tr` | `count` | 0.000 | 0.032 | −0.032 |
| `sinema_tr` | `proportion` | 0.000 | 0.153 | −0.153 |
| `sinema_tr` | `label_vs_label` | 0.192 | 0.500 | −0.308 |

### ⚠️ How this nearly shipped unmeasured, which is worth keeping

**Found 2026-09-16 while reconciling this datacard against the build, and it was
the "empty cell" failure mode again**, the same one that let `shift` survive four
gates. `scripts/style_solver.py` reads its majority baselines from
`manifests/baseline_report.json` and defaults to that path. The three new sets'
baselines had been written to the repo-root `baseline_report.json` instead, so
the solver found no baseline for them, recorded `majority_baseline: null`, and
propagated `lift: null` and `mean_lift: null` into `manifests/style_audit.json`.
The audit's summary line then reported a pass over the sets it *could* score and
said nothing about the three it could not. **A null in a lift column reads as
"nothing to report" when it actually means the check did not run.**

The raw solver scores had been recorded throughout and were low, so the outcome
was never in much doubt — but a raw score is not the gate. The gate is the score
minus the majority baseline, and on a near-binary family a solver scores close to
the baseline by construction, which is exactly why the subtraction is the part
that matters. The baseline files have been merged, the solver re-run over all
eleven configs, and the numbers above are that run.

**The durable fix, applied:** the gate command in the conventions section now
names all eleven sets for `trivial_baseline.py --out manifests/baseline_report.json`.
Naming only the original eight is how the split happened. A second hardening is
still open and worth doing: `style_solver.py` should **fail loudly on a missing
baseline** rather than emitting a null and continuing.

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

## Licensing — what can be published, verified 2026-08-25, revised 2026-09-16

⚠️ **This section changed materially in v0.7.0 and the v0.6.x version of it was
wrong for the current release.** It used to open "nothing here requires an email
or a permission request". That held while the benchmark was eight sets. It does
**not** hold now: **two of the eleven sets have no upstream licence at all and a
permission enquiry is outstanding on both.** Three sets, not one, therefore ship
without their text.

| set | source | licence | text redistributable? | obligation |
|---|---|---|---|---|
| `tr_intent`, `en_intent` (+paired) | AmazonScience/massive | **CC-BY-4.0** | yes | attribute; state changes |
| `vitamins_tr` | turkish-nlp-suite (Vitaminler.com) | **CC-BY-SA-4.0** | yes | **share-alike**; cite Altınok (ACL 2023) |
| `musteri_tr` | turkish-nlp-suite (Hepsiburada/Trendyol) | **CC-BY-SA-4.0** | yes | **share-alike** |
| `sinema_tr` | turkish-nlp-suite/BuyukSinema | **CC-BY-SA-4.0** | yes | **share-alike** |
| `marc_en` | SetFit/amazon_reviews_multi_en | **Apache-2.0** | yes | include licence |
| `amazon_hpc_en` | McAuley-Lab/Amazon-Reviews-2023 | repo has **no licence tag**; text under Amazon's Conditions of Use | **no** | withhold text |
| `sikayet_tr` | Kaggle `savasy/multiclass-classification-data-for-turkish-tc32` | **uploader declares none**; text scraped from a complaints site | **no** | withhold text; **enquiry open** |
| `interpress_tr` | Interpress news 270k (via `yavuzkomecoglu/interpress_news_category_tr`) | **card declares none** ("[More Information Needed]") | **no** | withhold text; **enquiry open** |

The HF release tags the last three `other` rather than guessing a licence;
`scripts/publish_hf.py` holds the authoritative policy and refuses to package a
set that is missing from it.

### The four things to be careful about

**1. Share-alike is contagious, and it now covers three Turkish sets.**
`vitamins_tr`, `musteri_tr` and `sinema_tr` are CC-BY-SA-4.0. Anything derived
from those subsets — including our haystacks, since they are concatenations of
the text — must be released under CC-BY-SA-4.0. This is why the release is
**packaged as one Hugging Face config per source**, each with its own licence tag,
rather than as a single dataset: one licence field cannot describe this
collection honestly, and merging them would force the strictest terms onto
everything.

**2. Three sets must ship without their text**, and the three are not equivalent.
All ship as **questions, answers and a manifest only**, with the haystack text
rebuilt locally by a deterministic script — which costs nothing, because the
build is byte-identical from the seed.

- `amazon_hpc_en` — no licence tag, and the text remains subject to Amazon's
  Conditions of Use. Investigated exhaustively (2b below). **Settled**: silence
  is not permission, withholding is the answer, and nothing in the release
  depends on getting a different one.
- `sikayet_tr` — the Kaggle uploader declares no licence and the text is scraped
  from a third-party consumer-complaints site, so there are potentially **two**
  rights holders. **Open.**
- `interpress_tr` — the dataset card declares no licence. The Apache-2.0 header
  on the Hugging Face **loading script** covers that script, not the data, and
  must never be cited as the data's licence. **Open.**

(A fourth such set, the CC-BY-NC-SA airline corpus, was withdrawn along with its
Turkish partner in v0.5.0, so the release carries no non-commercial clause.)

**2c. The two open enquiries are the largest unresolved item in the release, and
they are load-bearing.** `sikayet_tr` and `interpress_tr` supply **142 of the 259
very-hard questions**, so they are not sets the benchmark can simply drop if the
answer is no. Until each is answered, both are built, measured and shipped
text-free, and any write-up should say so rather than implying the licence
position is settled.

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

### Declared per source (read by `scripts/check_pair.py` / `scripts/check_solo.py`)

Three config fields are declared by hand because none is measurable from the
data, and the first withdrew a whole pair in v0.5.0. `text_provenance` is newer
(v0.6.2) and backfilled here from the facts already established in this
document — the MASSIVE pair is a **human localization** of English SLURP
(§ above), never machine translation, and every other corpus is natively written
Turkish/English with no translation step at all:

| set | `licence` | `label_provenance` | `text_provenance` |
|---|---|---|---|
| `tr_intent`, `en_intent` (+paired) | `cc-by-4.0` | `professional_annotation` | `human_translated` |
| `vitamins_tr` | `cc-by-sa-4.0` | `author_stars` | `human_written` |
| `musteri_tr` | `cc-by-sa-4.0` | `author_stars` | `human_written` |
| `sinema_tr` | `cc-by-sa-4.0` | `author_stars` | `human_written` |
| `marc_en` | `apache-2.0` | `author_stars` | `human_written` |
| `amazon_hpc_en` | `unknown` | `author_stars` | `human_written` |
| `sikayet_tr` | `unknown` | `crowd` | `human_written` |
| `interpress_tr` | `unknown` | `professional_annotation` | `human_written` |

Two v0.7.0 notes on `label_provenance`. `sikayet_tr` is `crowd` because the
category is chosen by the complainant when filing, not assigned by an annotator.
`interpress_tr` is `professional_annotation` because the section is the
publisher's own editorial desk assignment.

### Source revisions are pinned (2026-09-16)

Every fetch script under `scripts/` loads its source at a fixed Hub commit
(`REVISION` at the top of each file). The pinned commit is the one that was
HEAD when the source was fetched in August 2026, verified against the Hub's
commit history, so the pin reproduces exactly the bytes that were built. This
matters most for `amazon_hpc_en`, which ships without text: an upstream change
would otherwise have made its haystacks unrebuildable, and the manifest's source
hash could detect that but not recover from it.

| source | pinned commit |
|---|---|
| `McAuley-Lab/Amazon-Reviews-2023` | `2b6d039e` (2024-12-08) |
| `AmazonScience/massive` | `ff6bd8e4` (2022-11-16) |
| `turkish-nlp-suite/vitamins-supplements-reviews` | `c4c0928e` (2024-07-15) |
| `turkish-nlp-suite/MusteriYorumlari` | `7579c679` (2024-11-01) |
| `SetFit/amazon_reviews_multi_en` | `ec73b665` (2022-04-13) |
| `turkish-nlp-suite/BuyukSinema` | `137d0ff7` |

**Two v0.7.0 sources cannot be pinned this way, and both matter because neither
ships its text.**

- `interpress_tr` is not on the Hub as data at all: the repository contains only
  a loading script no current `datasets` version will run, and the script points
  at a plain HTTP archive with no revision history. The only reproducibility
  guarantee available is the **sha256 of what was downloaded**, which
  `scripts/interpress_tr.py` records as `EXPECT_SHA256` and verifies on every
  fetch (`f41659ed…46`). A rebuild that fails that check is not this dataset.
- `sikayet_tr` comes from Kaggle, which requires an account, so the script does
  not download at all — the user passes the path to their own copy of
  `ticaret-yorum.csv`. The manifest's `source_hash_first1000` is what ties a
  local rebuild back to the published build.

### Before release

1. `LICENSE` (MIT) covers **code only** — add a line saying so, since each data
   subset carries its own terms.
2. Re-check every source's licence page at release time and record the access
   date. Licence fields on Hugging Face do change.
3. Ship the per-source config split; do not flatten into one dataset.


## Could this be published tomorrow? Blockers, ranked

*Answered by events: v0.7.0 was published to Hugging Face on 2026-09-16. This
section is kept as the standing assessment, revised for what shipped.*

**Nothing legal blocks the release as packaged, but "licences are resolved" is
no longer accurate and that sentence has been removed.** Three of the eleven
sources are unlicensed; all three ship text-free, and the per-source config split
handles share-alike. What remains open is whether `sikayet_tr` and
`interpress_tr` can ever ship their text, which is a question about a *future*
release rather than a defect in this one.

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
   (see above) and five of the eleven sets (`vitamins_tr`, `musteri_tr`,
   `marc_en`, `amazon_hpc_en`, `sinema_tr`) have star-derived labels where
   classical noise is near zero by construction, so this is a datacard gap, not
   a defect. The two v0.7.0 additions that are *not* star-derived are untouched
   by the measurement: `sikayet_tr`'s category is chosen by the complainant and
   `interpress_tr`'s section by the publisher's desk, and neither has been
   sampled for noise.
4. **No timeline axis is built.** The reason has changed and the old wording
   should not be reused: it used to be "no Turkish source carries dates", and
   that is **no longer true** — `interpress_tr` ships with 2,457 distinct daily
   publication dates, the fetch script keeps a `date` column for exactly this
   purpose, and the builder ignores it. So this is now an unbuilt family on
   available data, not a data blocker. Name it as a limitation before a reviewer
   finds it, and do not claim the data does not exist, because it is in the
   release.
5. Haystacks within a tier share 20–38% of records at the longest tiers, so
   tier-level confidence intervals need clustered errors.
6. **The questions on the 3-class sets are not independent** (added
   2026-09-16). Every `musteri_tr` haystack asks `count` for all three labels
   and `proportion` for the same labels (44 of 45 `count` questions have a
   `proportion` twin on the same haystack and label), and the three
   label-ranking questions plus `label_vs_label` are determined by the same two
   numbers. Twelve questions per haystack carry about two continuous degrees of
   freedom and one bit (`shift`, withdrawn in v0.7.0). The unit of evidence on the review sets is the
   haystack, 15–20 per set, not the question. The intent sets are unaffected
   (one duplicate in 69).
7. **Under `relative`, a read-nothing reader scores 0.43–0.63 on the numeric
   families and the length axis is flat** (see the sampling section above).
   Both are properties of the metric on this task family, not defects in the
   data; they must be stated wherever a score is reported.

**Recommended sequence, and where it now stands:** release the dataset, run the
baselines, then submit the paper. **The first step is done** (v0.7.0, 16
September), the release timestamp establishes priority, and item 1 remains a
paper blocker rather than a release blocker.
