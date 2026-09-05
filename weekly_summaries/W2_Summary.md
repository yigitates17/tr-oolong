# TR-OOLONG — Week 2: advisor follow-up

*Prepared 2026-09-03. Numbers recomputed from the built data today.*

---

## 0. FIRST — a serious bug, found while answering question 2. **Now fixed.**

**All 118 entity questions (9.7% of the benchmark) were unanswerable. The
benchmark has been fixed, rebuilt, and re-gated — see §10 for what changed.**

The entity families ask about **brand attribution** — *"which of these brands got
the most positive reviews?"*, *"how many of brand X's reviews are neutral?"* But
the brand lives in a **metadata column that is never shown to the model**. The
haystack is review text joined by a separator and nothing else
([build_tr_oolong.py:632-648](src/build_tr_oolong.py#L632-L648) appends `text`
only — there is no branch that renders the entity).

**The evidence.** Gold answers against how often the brand appears anywhere in the
haystack, `vitamins_tr` `entity_count`:

| brand | gold answer | times the brand appears in the text |
|---|---|---|
| New Life | 20 | **0** |
| Aksu Vital | 21 | **0** |
| Selfit | 18 | **0** |
| Natures Supreme | 14 | **0** |
| Grintuss | 14 | **0** |
| Ocean | 92 | 11 |
| NBL | 12 | 3 |

The two columns are uncorrelated. Only **2.0%** of source reviews mention their own
brand. Across both entity-bearing sets, **22–25% of entity questions have no
candidate appearing anywhere in the haystack at all** — and even when a brand is
mentioned, the mention count has no relation to the gold count, because the gold
count comes from the hidden column.

**Why all four gates missed it.** Every solver we built tests for **shortcuts** —
can this be answered *too easily*. None tests **solvability** — can it be answered
*at all*. Worse, the prior oracle found `entity_argmax` answerable from corpus
priors (0.55–0.87) and we fixed it with per-haystack jitter, which pushed it
further from guessable — in the direction of impossible.

**Why OOLONG does not have this problem.** They print the conditioning variable on
every line: `Date: Dec 28, 2022 || User: 76063 || Instance: …`. Our
`COMPARISON.md` argues our entity "does not need to be printed inline" because it
is a real corpus column rather than synthetic metadata. **That reasoning is
wrong** — being real in the source does not help a model that only ever sees the
haystack.

**Options:**

| | effect |
|---|---|
| **(a) Print the entity inline and rebuild** — *recommended* | restores all 118 questions; costs ~5–8 tokens/record so lengths shift and all four gates must be re-run |
| (b) Drop the entity families | 1,221 → 1,103 questions, 9 → 6 families, and we lose the entity axis that makes `vitamins_tr`↔`amazon_hpc_en` the primary pair and is our main structural advantage over OOLONG |
| (c) Ship as-is | not viable |

**One check that (a) needs.** Printing the brand makes it string-matchable, so
`entity_count` must not become a counting-strings task — the exact "lexical, not
latent" criticism we level at ONERULER. It does not: the **label** stays latent, so
*"how many of brand X's reviews are negative"* still requires classifying every one
of brand X's records. Filtering becomes lexical; aggregation stays latent. That is
precisely OOLONG's design.

**The wider point for the meeting, and it is the publishable one:** every solver
we built asks whether a question is answerable **too easily**. None asks whether
it is answerable **at all**. A shortcut audit is not a validity audit, and the two
failure modes point in opposite directions — the prior-neutrality fix pushed
`entity_argmax` away from guessable and therefore further into impossible. One 4B
run over 20 entity questions would have caught this in an hour. It argues for
running the cheap baseline **now**, not for building more audits.

---

## 1. What is long context? Are we solving the cross-reference problem?

**"Long context" is not one task.** The useful axis is *what fraction of the
document you must process to answer correctly*:

| task type | what it needs | example | solvable by search? |
|---|---|---|---|
| **Retrieval / needle** | find one span | "what is the passkey?" | **yes** — grep works |
| **Multi-hop / cross-reference** | find a span, follow its reference, resolve the chain | **your law example** | partly |
| **Aggregation** | classify **every** record, then combine | OOLONG, TR-OOLONG | **no** |
| **Global summarisation** | compress everything | book summarisation | no, but no exact answer either |

**Our working definition, and we enforce it in code:** a task is long-context
*aggregation* if **the answer is a function of every record, and no proper subset
of the document determines it.** We measure this — the audit reports how many
records determine each answer, and questions resting on too few are rejected. An
early `pairwise` family rested on **8 records out of 3,919** with a margin of 2;
that is needle-retrieval with a coin flip, and it is the thing this benchmark
exists to replace. Depth and margin floors are now enforced in both ground-truth
paths.

**Are we solving your law-document problem? No — and I would not try to.** That is
*multi-hop reference resolution over discourse-structured documents*, and it
differs from ours on a property that matters:

- Our haystacks are **order-independent**. Shuffle the records and every answer is
  unchanged (except `shift`). They are a *bag* of records.
- A legal corpus is **order-dependent and referential**. Shuffle it and it is
  destroyed. Article 4 means nothing without the definition in Article 1.

Three reasons not to bolt it on: ground truth would need expert annotation of the
reference chains, which destroys the property that makes this benchmark exact and
free at 1M tokens; it is a different literature (legal NLP, multi-hop QA); and no
Turkish legal corpus with resolved cross-references exists as a labelled resource.

**It is the right thing to name as a limitation and as future work** — "we cover
aggregation, not referential resolution" — and it pairs well with the missing
timeline axis as the two axes we do not touch.

**One thing worth saying back to him:** artificial construction does not mean easy.
OOLONG's own result is that handing models the gold labels for free improves scores
by only 0.79–10.9 points. Concatenated records are not solved.

---

## 2. Label vs entity

- **Label** = the class being counted. It is **latent** — never written in the
  text, and we enforce that by dropping any record containing any label's surface
  form. You must *read and infer* it. (`olumlu`, `alarm_set`)
- **Entity** = a second field attached to each record that is **not** what is being
  classified and is **orthogonal** to the label (every brand receives all three
  sentiments). It is used to *condition*. (`Nutraxin`)

**Spreadsheet analogy:** the label is the column you compute statistics over; the
entity is the column you `GROUP BY`.

**On his specific question — "label A vs label B, more/less/same".** That is
OOLONG's family, and **we do not have it.** Ours is `pairwise`, which compares two
**entities**: *"'olumsuz' yorumu hangisinde daha çok: 'Centrum' mu yoksa 'Ncs'
mi?"* — same label, two brands. Theirs holds the population fixed and compares two
labels; ours holds the label fixed and compares two subsets. **Theirs is the easier
one to add and it needs no entity column**, so it would work on all eight sets
including the intent axis. Worth adding — it is a genuine gap and it is cheap.

---

## 3. The tokenizer — is using Qwen wrong?

**No, but the claim we draw from it has to be scoped.** Two separate uses:

**(a) As a ruler for haystack length — correct and necessary.** You need one fixed
tokenizer to define "100K tokens" consistently. `Qwen/Qwen3-8B` is the right choice
because it is the family we intend to evaluate. We also record `n_chars` in every
output so a reader can re-derive lengths under a different tokenizer.

**(b) As evidence that "Turkish costs 1.30–1.34× the tokens of English" — this is
where it breaks.** On the *same* 3,000 pair-aligned utterances:

| tokenizer | TR/EN token ratio |
|---|---|
| GPT-2 | **2.16×** |
| Qwen3-8B | 1.53× |
| mBERT cased | 1.29× |
| **BERTurk** | **0.57× — Turkish is cheaper** |

The ratio measures **how much Turkish the tokenizer saw in training**, not
agglutination.

**Why not a Turkish tokenizer?** Because the benchmark measures what *the models we
evaluate* actually pay. No frontier LLM uses BERTurk; using it would measure a
property of Turkish under a tokenizer nobody deploys.

**Should we mention it? Yes — it is a finding, not a weakness.** "The commonly
cited Turkish token-cost penalty is tokenizer-dependent and can reverse" is a small
publishable observation, and a reviewer from the Turkish NLP community would catch
it if we hid it. The safe framing: **name the tokenizer, report the spread, and
anchor the cross-lingual claim on the record-matched pair**, which compares at
equal *content* and therefore carries no token-budget confound at all.

---

## 4. Is the data real or synthetic?

**Real text, real labels, synthetic assembly.**

| layer | status |
|---|---|
| the text | **100% real** — customer reviews from Vitaminler.com, Hepsiburada, Trendyol, Amazon; real assistant utterances from MASSIVE |
| the labels | **real, and in 5 of 8 sets not annotations at all** — the star rating typed by the person who wrote the review. MASSIVE: professional annotation |
| **the assembly** | **synthetic** — which records go into which document, in what order, at what length, plus deliberate drift injection for `shift` |
| the questions | templated by the builder |

Same as OOLONG, which also concatenates real labelled datasets — except they
*additionally* synthesise the dates and user IDs, where our entity is a real column.
**We are less synthetic than they are on the metadata axis**, which is precisely
what made the §0 bug possible.

**One caveat worth knowing before he asks.** MASSIVE is a human *localisation* of
English SLURP utterances into 51 languages. The Turkish is human-produced but
translation-originated, not natively authored — so there is a translationese risk
on the intent axis. The review corpora are natively written Turkish and carry no
such risk. Worth one line in the limitations.

---

## 5. `tr_intent` vs `tr_intent_paired`, and what language are the labels?

| | matched on | Turkish document holds | answers correspond? | answers |
|---|---|---|---|---|
| `tr_intent` / `en_intent` | equal **token** budget (50K/100K) | **fewer** records (Turkish costs more tokens) | no | different |
| `tr_intent_paired` / `en_intent_paired` | equal **record** count (3K/6K), same records, same order | the same records, more tokens | **yes** | **110 of 120 byte-identical** |

They answer different questions — *"at equal cost, which language degrades
faster?"* versus *"at equal content, which degrades faster?"* Only the paired one
supports a paired statistical test.

**The labels are English**, in both halves. A Turkish question reads: *"Bu
kayıtlarda kaç tane **'recommendation_locations'** etiketli kayıt var?"* — Turkish
wording, Turkish text, English label identifier. This is only true on the intent
axis; on the review axis the labels **are** Turkish (`olumlu` / `olumsuz` /
`nötr`).

---

## 6. Should we translate the labels to Turkish? (`play_music` → `müzik_çal`)

**You were right and my first answer was wrong. Corrected below, with the
measurement.**

I argued translation would destroy a leakage asymmetry of 0.00% (Turkish) versus
0.68% (English). **That asymmetry is not in the build** — both intent sets record
`label_leakage_rate: 0.0`. The figure was stale. And the argument was wrong
anyway: Turkish text showing 0% against *English* label strings is a tautology,
not a finding. Turkish utterances do not contain the string `play_music` because
they are Turkish, not because Turkish morphology hides anything.

**What the measurement actually shows**, comparing each language against labels in
its *own* language:

| | leak rate |
|---|---|
| EN text vs **English** labels (`alarm_set`) | **0.00%** (0 / 15,075) |
| TR text vs **Turkish** labels (`alarm_kur`) | **0.91%** (137 / 15,075) |

```
label=alarm_kur   matched 'alarm kur'  | iki saat sonrasına alarm kur
label=alarm_kur   matched 'alarm kur'  | on ikiye alarm kur
label=alarm_kur   matched 'alarm kur'  | öğleden sonra dörde alarm kur
```

**The cause is word order, not morphology.** Turkish is verb-final, so a
`noun_verb` label name matches the natural phrase exactly. English `alarm_set`
never appears, because you say "set an alarm," not "alarm set."

**So the consequence of translating is real but mild:** ~137 records (0.9%) get
dropped by the leakage filter, and since the filter applies as a union over the
pair, the English half loses the same `pair_id`s. That is a 0.9% pool cost, not a
destroyed finding — and it is avoidable by naming labels non-phrasally
(`alarm_kurma`).

**My two remaining objections were also weak, and worth retracting explicitly:**

- *"It breaks the byte-identical answer."* `shift` answers were **already**
  language-specific (`arttı` / `rose`), and `label_vs_label` now is too. The twin
  check maps them to a canonical outcome and verifies they agree. Translated
  labels would work the same way.
- *"It adds a hand-made artifact."* We already hand-map stars to
  `olumlu`/`olumsuz`/`nötr`. The intent axis is the inconsistent one.

**Where it lands:** the decision is defensible either way, and `licence` /
`label_provenance` style declaration is the right pattern — so it belongs in the
config, not hardcoded. It is worth building `tr_intent_translated` as an ablation:
the "English label as a free hint in the language the model is stronger in"
question is real, and the extra filter drop is now measured rather than guessed.

## 7. What "spread" means in the length table

**`spread = mean words of the longest-averaging class ÷ mean words of the
shortest-averaging class`.**

So `vitamins_tr` at 1.5× means: `olumsuz` records average **15.0 words**, `olumlu`
records average **9.8 words**, and 15.0 / 9.8 = 1.53. A spread of 1.0 means length
tells you nothing about the label.

It is a crude ceiling on how much of the label a **length-only** classifier could
recover. The builder warns at **≥ 2.0×**; the withdrawn We-Bears corpus was 3.6×.

**It is a screening heuristic, not the gate.** The real gate is the style solver's
measured lift on *built questions*, because source-level spread does not predict
question-level exploitability — the lesson that cost us a whole rebuilt corpus pair.

---

## 8. Synthetic data and synthetic labels — pros and cons?

Three different things, and they have different answers:

**(a) Synthetic *composition* — what we do. Right call.**
*Pro:* ground truth is **exact and free at any length**. Nobody could hand-annotate
"how many negative reviews are in this 1M-token document"; we get it for nothing.
Length, class balance and drift become controllable knobs, so difficulty is a
gradient we set. Fully reproducible and regenerable, which is what makes twins
possible at all.
*Con:* the document is not a naturally occurring document — no discourse, no
coreference, no cross-references (§1).

**(b) Synthetic *text* (LLM-generated reviews) — no.**
*Pro:* unlimited data, perfect control, and it would solve our Amazon licensing
problem outright.
*Con:* it would **destroy the cross-lingual claim.** LLM-written Turkish is not
Turkish as written by Turkish speakers; measuring "does Turkish degrade recursive
compression" on model-generated Turkish measures the *generator*. It is also
circular — evaluating LLMs on LLM-written text — and reviewers are increasingly
hostile to it.

**(c) Synthetic *labels* (model-assigned) — definitely not.** The benchmark would
measure agreement with the labelling model rather than correctness, and it is
exactly what we suspect We-Bears of (§4.2 of last week's summary). We cannot drop a
corpus for undocumented label provenance and then generate our own.

**"Can synthetic give better results?"** Better *numbers*, sometimes — zero label
noise, perfect balance. Better *evidence*, no: you have swapped a measurement of
real-language ability for a measurement of imitation-language ability.

**The one legitimate use** is as a **diagnostic control**, not as the benchmark —
e.g. a synthetic set with perfectly uniform record length to isolate the length
confound from the language effect. That is a good use and worth keeping in mind.

---

## 9. A compatibility checker for new language pairs — should we build it?

**Yes. This is the strongest suggestion of the batch, and we already have most of
it.**

Three reasons it is worth doing:

1. It converts the project from *"a Turkish benchmark"* into *"a method for building
   matched-twin benchmarks in any language pair"* — a larger and more citable
   contribution, and it is what makes the repo reusable by anyone else.
2. **~70% already exists.** `--audit` already reports, per source: rows after
   cleaning, label space, entity askability, mean tokens per record, feasibility at
   each length tier, class imbalance and normalised entropy, per-class surface shape
   with the length-spread warning, entity-axis viability, and trial-haystack rank
   gaps. After a build, three more solvers run.
3. **What is missing is exactly what he described: a pairwise mode.** Everything
   today judges one source at a time; nothing compares two.

**What `check_pair.py` would report**, mapping onto the four twin criteria:

| check | pass condition | why it matters |
|---|---|---|
| label provenance | both **declared**, and the same kind | the defect that killed We-Bears; cannot be automated — must be a declared field |
| label space | same K, with a declared 1:1 mapping | a 3-class vs 5-class pair is not a twin |
| record length | ratio under ~2.5× | changes what "one chunk" means |
| surface-shape gap | \|spread_A − spread_B\| small | an asymmetric format shortcut is what breaks the cross-lingual claim |
| class balance | both entropies, and the gap | |
| reachable tiers | `R_max = smallest_class × K` on both halves | both must reach the same lengths |
| entity axis | present or absent on **both**; MI(entity, label) low | a twin whose halves support different families is not a twin |
| **licence** | both redistributable, else flag | the veto |

**The verdict should not be binary** — `compatible` / `compatible with caveats` /
`incompatible`, each with the reason and the number.

**And the validation story is already sitting in our history:** run it on our own
candidates and it should return `musteri↔marc` compatible, `vitamins↔amazon`
compatible-with-caveats (3.7× length mismatch, licence asymmetry), and
**`We-Bears↔airline` incompatible** — i.e. **the tool would have rejected the pair
we dropped, before we spent weeks building it.** That is the argument for it.

**Turkish-only or Turkish-English?** Turkish-English. A Turkish-only set is
buildable, but without a twin you cannot separate *"the model is bad at this task"*
from *"the model is bad at Turkish"* — the twin **is** the methodology. The tool
should still keep a single-source mode, since that is what `--audit` already is.

**Effort:** mostly assembling existing measurements into a pairwise report plus a
small declared-metadata schema. Two or three days.

---

## 10. What was actually done this week (v0.6.0)

All five gates are green and the benchmark is rebuilt.

**1. The entity bug is fixed.** Records now render as `[[Nutraxin]] <review text>`.
The marker is symbol-only on purpose: `Marka:` / `Brand:` would tokenize
differently in each language and reintroduce a confound into the matched twin.

Three follow-on changes the fix required, each found by a gate:

- **A build-time guard.** Emitting an entity family with `render_entity=false` now
  **raises**. The defect cannot recur silently.
- **The leakage filter now masks the rendered record, not the raw text.** Printing
  brand names ships them, and `verify_release` caught `The Pressure Positive Co.`
  in `amazon_hpc_en` handing the label `positive` to a substring solver — 1 brand,
  52 rows, 0.09%. Dropped.
- **`verify_release` reconstructs haystacks with the prefix**, or every set fails.

**Does printing the brand make the family lexical?** No — and this was the check
that mattered, because "lexical rather than latent" is exactly our criticism of
ONERULER. The **label stays latent**: *"how many of brand X's records are
negative"* still requires classifying every one of them. Verified on the rebuild —
e.g. `Venatura` appears 47 times, and the gold answer for one label is 10.

**2. `label_vs_label` added** — OOLONG's "is A more, less, or equally common than
B", which we lacked (§2). It needs no entity column, so it ships on all eight sets.
The outcome is drawn first and a label pair searched for that realizes it,
otherwise "same" would never be the gold answer and a model that never says "same"
would lose nothing.

Two honest notes: it is **3-way at 48 classes and 2-way at 3** ("eşit" is 5 of 10
answers on `tr_intent_paired`, and never fires on the 3-class review sets, because
Dirichlet-drawn class shares are far apart). And it is **the least stable family** —
it widened the `musteri_tr`↔`marc_en` twin asymmetry from **0.010 to 0.070**, still
well inside the +0.15 gate but now the worst of the four pairs.

**3. `scripts/check_pair.py`** (§9). Reproduces our own §11 verdicts:

| pair | verdict |
|---|---|
| `musteri_tr` ↔ `marc_en` | **COMPATIBLE** |
| `vitamins_tr` ↔ `amazon_hpc_en` | COMPATIBLE WITH CAVEATS (3.3× length, Amazon licence) |
| `tr_intent` ↔ `en_intent` | COMPATIBLE WITH CAVEATS |
| `tr_intent` ↔ `marc_en` | **INCOMPATIBLE** (provenance, label space, 6.1× length) |

It required declaring `licence` and `label_provenance` in every config — neither
is measurable from the data, and undeclared provenance is what withdrew a pair in
v0.5.0, so the checker **fails** a pair that leaves either blank.

**The benchmark after the rebuild:**

| | before (v0.5.0) | after (v0.6.0) |
|---|---|---|
| questions | 1,221 | **1,254** (630 tr / 624 en) |
| families | 9 | **10** |
| haystacks | 110 | 110 |
| tokens | 28.2M | **28.3M** |
| **answerable entity questions** | **0 of 118** | **all 94** |
| gates | 4 green | **5 green** |

*(Entity questions went 118 → 94 because rendering costs ~5–8 tokens per record,
so each haystack holds fewer records and some draws no longer clear the
difficulty floors.)*

---

## Where this leaves us

**Done since the meeting (v0.6.0):** entity rendering fixed and rebuilt (§0);
OOLONG's label-vs-label family added on all eight sets (§2); `check_pair.py`
written and tested (§9); all five gates green. One stale claim was withdrawn in
the process — the MASSIVE leakage asymmetry (en 0.68% vs tr 0.00%) is **not in
the shipped build**, which measures 0.00% on both, and the comparison was
confounded by matching both locales against the *English* label vocabulary.

**Do first:** run one 4B model over a handful of questions per family. That is
the check that would have caught §0 in an hour, and it is still the top open item.

**Ablations, not blockers:** Turkish label translation (§6), the trajectory
language conditions (last week's §8.4).

**State as limitations:** no referential/multi-hop axis (§1), no timeline axis,
MASSIVE translationese (§4), tokenizer-dependence of the token-cost claim (§3).
