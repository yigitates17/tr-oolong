# TR-OOLONG: Week 6

*Draft, 11 October 2026. The main text is one page; the appendices hold the
detail.*

## 1. Summary

This week the benchmark's design was checked against OOLONG's construction
code, which has now been released, and against a native-speaker review of the
labels. Two findings changed the plan. First, the close comparisons introduced
in week 5 are decided by very few records: changing the label of a median of
7 records turns the answer into a tie, against 27 to 48 in the OOLONG questions
measured. Real labels are not that reliable, so in a simulation even a reader
of the whole document scores well below 1.0 on them. Second, OOLONG's own code
does not ask such near-ties. The benchmark
will therefore follow OOLONG's design as closely as possible, and keep its own
additions (close comparisons, Turkish-English pairs, shortcut checks) as a
clearly separate extension. The datasets are being simplified at the same time:
sentiment becomes positive/negative only, the news set is dropped, and
fine-grained categories are grouped.

## 2. What was found

**Close answers are fragile.** *Example:* a document holds 1,000 positive and
984 negative shopping reviews. If 8 of the positive reviews are really
negative, the counts tie at 992; 9 reverse the answer. 8 records are 0.3% of
the document. Across all core questions the median is 7 records to a tie (0.18%
of a document). In 184 sampled OOLONG questions it is 27 to 48 records (about
7%).

| simulated reader (a program, errors spread evenly over the labels) | correct on core questions |
|---|---:|
| reads a random half, with the true label of every record | 0.63 |
| reads everything, disagrees with 10% of the labels | 0.70 to 0.80 |
| reads everything, disagrees with 5% of the labels | 0.78 to 0.89 |

Under this simple error model the core score measures label agreement as much
as reading; real errors may be uneven, so these figures are an illustration,
not a measured limit. The week 5
statement that core questions show whether a model read the whole document no
longer holds as written.

**Random counts are easy to skim.** When each document's label mix is drawn at
random, as in OOLONG, two labels usually differ by about a third, and a random
5% of the records picks the larger one 76% of the time (9,656 label pairs in
TR-OOLONG's ordinary documents). Neither extreme works on its own.

**The labels need simplifying.** In a blind review (the reviewer labels each
record without seeing the source label, which is shown afterwards), the
disagreements had clear patterns:

- *Sentiment:* almost all involved "neutral", typically a review that praises
  the product and complains about delivery. Many short reviews say nothing
  about the product at all ("ürün geç geldi").
- *Complaints:* neighbouring categories, e.g. a laptop complaint filed under
  "computer" rather than "electronics", or a butcher chain under "venues".
- *Voice commands:* intents within one topic, e.g. "reply to Veysel's last
  email" labelled as sending an email rather than reading one.
- *News:* records are scanned print pages, sometimes several items run
  together (a National Geographic photo page filed under "travel"), and the
  sections overlap (technology / IT / communication).

Agreement with the source labels, Turkish (blind labels; "unclear" = the
text does not decide; intervals are 95%, with 20 to 40 records per dataset):

| dataset | unclear | agreement | after grouping |
|---|---:|---:|---:|
| shopping reviews | 10% | 100% (82-100) | |
| film reviews | 15% | 88% (66-97) | |
| supplement reviews | **40%** | 92% (65-99) | |
| voice commands | 15% | 59% (42-74) | 81% (64-91): 18 topics, "quirky" removed |
| complaints | 15% | 56% (39-71) | 81% (65-91): 12 groups, two catch-alls removed |

Positive/negative labels are reliable when a review gives an opinion. The
problem is reviews that give none: 40% of the supplement reviews checked are
about delivery or say nothing yet ("kısa sürede geldi umarım memnun kalırım").
A simple check estimates that 0.1 to 0.2% of the review records are not
Turkish (English or Azerbaijani). The groupings were chosen after seeing part
of this review, so they are checked on fresh records (section 4). The English
sheet is not reviewed yet.

## 3. What changes

| change | reason | follows OOLONG |
|---|---|---|
| sentiment is positive/negative only; middle ratings removed | "neutral" was the main source of disagreement | yes, OOLONG uses one positive and one negative label |
| news set removed | scanned pages, overlapping sections, and the text cannot be redistributed | yes, OOLONG uses only tasks its authors can do without difficulty |
| 48 voice-command intents grouped into the dataset's own 18 topics | most disagreements were inside one topic | yes, OOLONG merges similar labels |
| 29 complaint categories merged into 12 groups; two catch-alls removed | same | same |
| OOLONG's rules for comparisons: "most common" only when one label leads by more than 2% of the document; "A or B" only when they differ by more than 2% or are exactly equal | answers survive a few wrong labels | yes |
| close comparisons kept as a separate extension, built at a fixed series of gaps, each with the labels shown and hidden | they are this work's addition; showing the labels separates counting from classifying | no, deliberate |
| brand and company knowledge allowed ("Köfteci Yusuf" is a food chain) | many complaints cannot be classified otherwise | not stated in OOLONG |

None of these is built yet. They will be applied in one rebuild after the
review.

Also fixed in the candidate version (after an independent review on 7
October): the wording of ranking questions now says "among these labels"; "the
same" now means exactly equal; percentages state that halves round up;
identical texts with conflicting source labels are removed; answer positions are
shuffled (before, alternating between the two options answered every core
question correctly for anyone who knew the release order); 10% of the data is
kept aside for development so that the test documents are not tuned.

## 4. Status and open items

- Label review: Turkish complete (140 records; news skipped after it was
  dropped); English 0 of 80. The groupings are now fixed and are checked on a
  fresh sample of Turkish records that were not used to choose them.
- Candidate new datasets (appendix C), under consideration. The aim is one
  Turkish counterpart per OOLONG task.
- No AI model has been run. Model runs start once the dataset is final.

**Decisions required.**
1. **The benchmark's main claim.** Proposed: "OOLONG's design applied to
   Turkish, with English counterparts and parallel data, plus an extension
   that measures whether a method read the whole document". The week 5 claim
   (core questions show complete reading) is withdrawn.
2. **Which datasets make up the final version** (appendix C).

---

## Appendix A. What OOLONG does (paper version 2, 5 October 2026, and its code)

- **Real records, synthetic assembly.** OOLONG-synth takes records from 10
  public classification datasets. What is synthetic is how documents are put
  together: each document's label mix is drawn at random, and a made-up user id
  and date are attached to every record. OOLONG-real uses transcripts of a
  role-playing show, with answers from fan-made statistics.
- **Label quality.** Sentiment is reduced to positive/negative, similar labels
  are merged, at most 10 labels per dataset. Two AI models classify every
  record and records both get wrong are removed (0 to 0.6% per dataset).
- **Few near-ties.** "Most common" is asked only when one label leads by more
  than 2% of the document; "A or B more common" only when the two differ by more
  than 2% or are exactly equal ("same frequency"). "Least common" can be tied.
  The paper uses 25 questions per document, two documents per dataset and
  length.
- **Format.** One record per line; the document states how many records there
  are and lists the labels; numbers are scored 0.75 to the power of the error.
- **New in version 2:** the statement that for OOLONG-synth "all or nearly all
  of the lines are necessary", and a retrieval experiment concluding that
  OOLONG "cannot be easily solved by a simple agentic retrieval system". The
  week 5 measurement qualifies this: about a third of its questions name one
  user or month, which is printed on every record, so plain text search finds
  the relevant records.
- **Code** for building OOLONG is now public (MIT licence). TR-OOLONG can run
  a pinned copy of OOLONG's generator with a short, published list of changes
  (Turkish templates, measured token lengths, and two bugs found in the
  released code), so the claim is "adapted from OOLONG's generator" rather than
  a re-implementation.

## Appendix B. The RLM paper's use of OOLONG

The RLM paper (accepted at NeurIPS 2026) tests on 50 OOLONG questions from one
dataset at one length (131K tokens), and on OOLONG-Pairs, 20 questions from the
same data whose answers need pairs of records. All tests are in English. Its
8-billion-parameter model was trained on English tasks. It does not measure how
much of the input a method read.

## Appendix C. Candidate datasets

| dataset | language | task | why |
|---|---|---|---|
| dataset | language | task | status |
|---|---|---|---|
| XNLI | Turkish + English, the same sentences, human-translated | does one sentence follow from another (3 labels) | same task as OOLONG's MultiNLI; 7,500 pairs, so documents up to about 128K tokens; translation quality being checked by a native speaker |
| OffensEval-TR 2020 | Turkish (English sibling exists) | offensive or not | optional; the licence covers the labels, not the tweet text |
| OOLONG's own English data | English | 10 tasks | an anchor for the English side; scores are comparable with OOLONG's only where the construction is the same |

Rejected after inspection: a Turkish movie-review set (65% of its reviews are
already in the film subset); TTC-4900 (text preprocessed, no punctuation,
duplicates); TurkishHateMap (19 of 4,407 records are "hate"); a large Turkish
topic set that turned out to be machine-generated; SIB-200 (parallel but only
1,004 sentences per language).
