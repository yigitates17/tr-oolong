# TR-OOLONG — Week 2

*Written for someone who has not read the code. Every number here comes from the
built dataset, not from a plan. Updated 2026-09-07.*

---

## 0. Where we are, in one glance

| | |
|---|---|
| **Built** | 110 documents · **1,254 questions** · 28.3 million tokens |
| **Languages** | Turkish 630 questions · English 624 |
| **Question types** | 10 |
| **Document sizes** | 36,000 → 988,000 tokens (the biggest is ~2,000 pages of text) |
| **Automatic checks** | 5, all passing |
| **Can it be published?** | **Yes — the dataset could go out tomorrow.** The *paper* needs one more thing (§2) |

**What changed this week:** we found and fixed a serious bug, measured something
we had only guessed at, and withdrew a claim that turned out to be wrong.

---

## 1. The bug we found — and why it is the most important thing here

### What was broken

Some of our questions ask about **brands**, like:

> *"Which of these brands got the most positive reviews: Beeo, NBL, Nbt İlaç,
> Smartcaps, Suda Collagen?"* → **Smartcaps**

The brand name was stored in a **separate column in our files** — but it was
**never printed into the text the model actually reads**. The model saw only
review text:

```
İndirim zamanı buradan alınabilir, paketlemesi de gayet güzel
<<<###>>>
Başkası için aldım ama sürekli kullanıyor 🙏🏻
```

No brand anywhere. So the model was asked *"how many Venatura reviews are
neutral?"* — answer **10** — while the word "Venatura" appeared **zero times** in
the document. **Nobody and nothing could have answered it.**

**118 questions — 9.7% of the whole benchmark — were impossible.**

### Why our automatic checks did not catch it

This is the part worth explaining, because it is a lesson rather than an accident.

We had built four "cheating detectors". Each one asks: **can this question be
answered too easily, without really reading?** None of them asked the opposite
question: **can it be answered at all?**

> **Simple analogy:** we had built four different anti-cheating systems for an
> exam, and never checked that the exam questions had answers.

One detector even made it worse. It noticed that brand questions were slightly
guessable from general statistics, so we added randomisation to make them harder.
That pushed them further from "guessable" — in the direction of "impossible".

### How we fixed it

Every record now prints its brand in front of it:

```
[[Nutraxin]] ürün güzel fakat kokusu çok ağır
<<<###>>>
[[GetDirect]] orijinal ürün, güvenilir mağaza
```

**Why the double brackets instead of writing "Marka:" or "Brand:"?** Because a
real word would be a different word in each language, and would be split into a
different number of tokens in Turkish than in English. That would quietly make
the two halves of our comparison unequal. Symbols are identical in both.

**Does printing the brand make the question too easy now?** No, and this matters:

- Finding **which** records are Nutraxin → now easy (search for `[[Nutraxin]]`)
- Deciding **which of those are positive** → still requires reading Turkish

The brand appears 47 times; the answer is 10. You still have to read 47 reviews
and judge each one. **The easy half became possible; the hard half is untouched.**

### The safety net

The builder now **refuses to run** if a config asks brand questions without
printing brands. This exact bug cannot come back silently.

---

## 2. Can we publish tomorrow?

**The dataset: yes.** Nothing blocks it.

- All licences are resolved. Seven of our eight sets can be redistributed freely.
- The eighth (Amazon) has **no licence at all**, so we ship its questions and
  answers but **not its text** — users rebuild the text locally from a script.
  Silence from Amazon is not permission.
- We tested the publishing script end to end this week. It works.

**The paper: not yet — one thing is missing.**

> **No model has ever been run on our benchmark.**

Everything we say about difficulty today is *theoretical* — "a random guess would
score 20%". We have never said "GPT-5 scores 34%". A reviewer will ask for that
immediately, and they should.

**Recommended order:** release the dataset now (it timestamps the work and costs
nothing), run the models, then submit the paper.

---

## 3. OOLONG vs TR-OOLONG, with real examples

**OOLONG** (Bertsch et al., 2025) is the English benchmark we build on. It glues
together thousands of labelled records and asks questions about the *statistics*
of the whole pile — so you cannot answer by searching, you must read everything
and count.

**TR-OOLONG** does the same for **Turkish**, and pairs every Turkish set with an
English twin built by the identical pipeline — so any difference we measure is
about *the language*, not about the benchmark.

### The same question, both benchmarks

| | OOLONG | TR-OOLONG |
|---|---|---|
| **Most common label** | *"Which label is most common: ham, spam?"* → `spam` | *"Bu yorumlarda en sık görülen etiket hangisi?"* → `olumlu` |
| **Count one label** | *"How many are 'ham'?"* → `4` | *"Bu yorumlardan kaç tanesi 'nötr'?"* → `881` |

**Notice the size difference.** Their answers are single digits. Ours run to the
thousands. That broke their scoring formula, so we added a second one (§4.7).

### What each of us has that the other does not

| Question type | OOLONG | TR-OOLONG |
|---|:---:|:---:|
| Most / least common label | ✅ | ✅ |
| Count a label | ✅ | ✅ |
| **Label A vs label B** (more / less / equal) | ✅ | ✅ **added this week** |
| **What percentage** have label X | ❌ | ✅ |
| **Second** most common label | ❌ | ✅ |
| Group by **brand** (real brands) | ❌ | ✅ |
| Group by **user ID** (invented IDs) | ✅ | ❌ |
| **Questions about real dates** | ✅ | ❌ **our real gap** |

### The gap we cannot close yet — dates

OOLONG stamps a **date on every line**, so it can ask things we simply cannot:

> *"Only consider instances from October — which label is most common?"*
> *"How many dates appear exactly once?"*

We have **no date column in any Turkish dataset we could find**. Instead of time,
we split the document in half by **position** and ask:

> *"In the second half of the reviews, did 'olumsuz' go up or down compared to the
> first half?"* → **azaldı** (went down)

**This is our weakest question type**, and we say so openly: it has only two
possible answers (so guessing scores 50%), and it is the only type our
"dumb program" test can partly beat.

**It is blocked on data, not on effort.** More in §7.

---

## 4. The advisor's questions, answered

### 4.1 What is "long context"? Are we solving the legal cross-reference problem?

"Long context" is not one problem. The useful way to split it is: **how much of
the document must you read to answer?**

| Type | What it needs | Example | Can you just search? |
|---|---|---|---|
| **Find a needle** | one sentence | *"What is the password?"* | **Yes** |
| **Follow a reference** | a chain of links | *"Article 4 refers to a definition in Article 1"* | Partly |
| **Aggregate** ← **us** | **every single record** | *"How many are negative?"* | **No** |
| **Summarise** | everything, loosely | *"Summarise this book"* | No |

**Our definition, which we enforce in code:** the answer must depend on *every*
record, and **no small piece of the document may determine it**. We measure this.
An early version had a question whose answer rested on **8 records out of 3,919** —
that is a needle hunt with a coin flip, and we deleted it.

**Are we solving the legal cross-reference problem? No — and we should not try.**

The difference is real:

- **Our documents are a bag.** Shuffle the records and every answer stays the
  same. Order carries no meaning.
- **A legal document is a chain.** Shuffle it and it is destroyed. Article 4
  means nothing without Article 1.

Three reasons not to add it: the correct answers would need expert lawyers
(destroying the thing that makes our benchmark free and exact); it is a different
research field; and no Turkish legal corpus with resolved references exists.

**We name it as a limitation.** That is the honest and correct move.

> **Worth saying to him:** artificial construction does not mean easy. OOLONG's
> own finding is that *giving models all the correct labels for free* improves
> their scores by only 0.79–10.9 points. The hard part is not reading each item.
> It is combining thousands of them.

### 4.2 What is the difference between a label and an entity?

| | **Label** | **Entity** |
|---|---|---|
| What it is | the thing we count | the thing we group by |
| Example | `olumlu` / `olumsuz` / `nötr` | `Nutraxin`, `Solgar` |
| Is it written in the text? | **No — it must be worked out** | Yes (we print it, §1) |

> **Spreadsheet analogy:** the label is the column you compute statistics on. The
> entity is the column you group by.

**On his specific question — "label A vs label B":** that was OOLONG's, and we did
not have it. **We added it this week.** It needs no brand column, so it works on
all eight sets:

> *"Are there more 'olumsuz' records or more 'olumlu' records, or the same
> number?"* → **daha az** (fewer)

Our older `pairwise` type compares two **brands**, not two labels — a different
question:

> *"Which has more 'olumlu' reviews: Shorne or Tab?"* → **Tab**

### 4.3 The tokenizer — we used Qwen. Is that wrong?

A **tokenizer** is the tool that chops text into the pieces a model actually
counts. Different models chop differently.

**Using Qwen as a ruler: correct.** You need one fixed ruler to say "this document
is 100,000 tokens", and Qwen is the model family we plan to test.

**Using it to prove "Turkish costs more tokens than English": not safe.** On the
*exact same sentences*:

| Tokenizer | Turkish costs |
|---|---|
| GPT-2 | **2.16×** English |
| Qwen3-8B | 1.53× |
| mBERT | 1.29× |
| **BERTurk** (Turkish-specific) | **0.57× — Turkish is CHEAPER** |

So the number measures **how much Turkish the tokenizer was trained on**, not
Turkish grammar.

**Why not just use a Turkish tokenizer?** Because we measure what *real models we
test* actually pay. No frontier model uses BERTurk.

**Should we mention this? Yes — it is a finding, not a weakness.** "The widely
repeated claim that Turkish costs more tokens depends entirely on the tokenizer,
and can even reverse" is a small, publishable observation. Hiding it would be the
risk — a Turkish NLP reviewer would spot it instantly.

### 4.4 Is our data real or synthetic?

**Real text. Real labels. Artificial assembly.**

| Part | Status |
|---|---|
| The review text | **100% real** — written by real customers on real sites |
| The labels | **Real, and mostly not opinions** — 5 of 8 sets use the star rating the reviewer themselves gave |
| **The documents** | **Artificial** — *we* choose which reviews go together, in what order, and how long |
| The questions | Generated from templates |

**Why "the writer's own star rating" matters so much:** nobody had to guess
whether a review was positive. The customer clicked 5 stars. There is no
annotator to disagree with.

**One caveat to know before he asks:** the MASSIVE dataset (our Turkish/English
matched pair) is a **human translation** of English sentences into Turkish. So
that Turkish is real Turkish, but *translated* Turkish, not originally-written
Turkish. Our review datasets have no such issue.

### 4.5 `tr_intent` vs `tr_intent_paired`, and what language are the labels?

We built the same data two ways, because they answer different questions:

| | Matched on | Asks |
|---|---|---|
| `tr_intent` / `en_intent` | **Same token budget** (both 100,000 tokens) | *"At equal cost, which language is harder?"* |
| `tr_intent_paired` / `en_intent_paired` | **Same records**, same order | *"At equal content, which language is harder?"* |

The paired version is the powerful one: **100 of 120 questions have exactly the
same correct answer in both languages.**

> Turkish: *"Bu kayıtlarda kaç tane 'transport_taxi' etiketli kayıt var?"* → **18**
> English: *"How many utterances have the intent 'transport_taxi'?"* → **18**

Same question, same answer, different language. Any score difference **is** a
language difference.

**The labels are in English** (`transport_taxi`) even in the Turkish set — because
they are database codes from the original dataset, not words. On the review sets
the labels *are* Turkish (`olumlu`, `olumsuz`, `nötr`), because there they are
ordinary words.

### 4.6 Should we translate the labels into Turkish? (`play_music` → `müzik_çal`)

**You were right to push on this, and my first answer was wrong.** I claimed it
would break a finding about Turkish grammar. Checking the actual data:

- That finding **is not in our current dataset** — the number I cited was from an
  older version. Withdrawn (§5).
- Your reasoning was sound: `play_music` gives the answer away in English, so
  `müzik_çal` giving it away in Turkish is **symmetric**, which is fair.

But measuring it properly showed something real, in the **opposite** direction
from what I said:

| | How often the text gives away its own label |
|---|---|
| English text vs English labels (`alarm_set`) | **0.00%** |
| Turkish text vs Turkish labels (`alarm_kur`) | **0.91%** |

**The reason is word order, not grammar complexity.** Turkish puts the verb last,
so a label named `alarm_kur` matches a natural Turkish sentence exactly:

> *"iki saat sonrasına **alarm kur**"* → label `alarm_kur` ✗ gives itself away

English never does this — you say *"set an alarm"*, never *"alarm set"*.

**Conclusion: translating is possible and costs ~0.9% of the data** (those rows get
filtered out). It is a reasonable experiment, not a default. Keeping English codes
loses **no Turkish signal**, because the Turkish is in the *text* the model reads —
the label is just the name of the bucket.

> Sorting Turkish emails into folders labelled in English does not make the emails
> less Turkish.

### 4.7 What does "spread" mean? — with an example

**Spread = how much longer the wordiest class is than the shortest class.**

Concretely, on our Turkish vitamin reviews:

- `olumsuz` (negative) reviews average **15.0 words**
- `olumlu` (positive) reviews average **9.8 words**
- **15.0 ÷ 9.8 = 1.5×** ← that is the spread

**What it means in plain terms:** negative reviews are one and a half times longer
than positive ones.

**Why we care:** if that number is big, you can guess the label **without reading
the words at all** — just by measuring how long the review is.

| Spread | Meaning |
|---|---|
| **1.0×** | Length tells you nothing. Perfect. |
| **1.5×** | Mild. Fine. |
| **2.0×** | Our warning line |
| **3.6×** | The dataset we deleted (§5) |

### 4.8 "Long comment = negative" — and the case where it reverses

The common pattern: **unhappy customers write more.** An angry customer explains
what went wrong; a happy one writes "güzel ürün".

We wrote a deliberately stupid program to test this. It reads **no words at all**.
It only looks at:
1. how long the text is
2. does it end with a full stop
3. does it contain `!` or `?`

Then it tries to answer our questions. Here is what it found:

| Dataset | Longest class | Shortest class | Spread |
|---|---|---|---|
| `vitamins_tr` | olumsuz 15.0 w | olumlu 9.8 w | 1.5× |
| `musteri_tr` | olumsuz | olumlu | 1.2× |
| `marc_en` | negative | positive | 1.1× |
| **`amazon_hpc_en`** | **positive 46.9 w** | negative 41.8 w | 1.1× |
| *deleted dataset* | *olumsuz 33.1 w* | *olumlu 9.1 w* | ***3.6×*** |

### **The reversal — this is the interesting bit**

Look at `amazon_hpc_en`. **The positive reviews are the LONGER ones.**

The "angry customers write more" rule is **not universal**. On Amazon
health products, satisfied buyers write long enthusiastic reviews — *"I have been
suffering for months with heel pain and this finally…"* — while unhappy ones write
*"Didn't work."*

**So the direction depends on the website, not on human nature.** This is exactly
why we measure it per dataset instead of assuming.

### How we handle it

A dataset where length predicts the label is **still a valid counting task** — the
model must still classify thousands of records and add them up. What it stops
being is a test of **reading Turkish**.

That only becomes fatal when the effect is **lopsided between our two languages**.
If Turkish leaked through length but English did not, a model could score well on
Turkish by measuring sentence lengths — and our whole comparison would be fake.

**So the number we actually check is the GAP between the two halves of a pair:**

| Pair | Gap |
|---|---|
| Turkish/English matched records | **0.014** |
| `vitamins_tr` ↔ `amazon_hpc_en` | 0.020 |
| Turkish/English matched tokens | 0.028 |
| `musteri_tr` ↔ `marc_en` | 0.030 |
| *the pair we deleted* | ***0.108*** |

Small = the two halves behave the same = the comparison is trustworthy.

---

## 5. What we withdrew — an honest correction

We had been claiming, in five documents:

> *"English text reveals its own label 0.68% of the time; Turkish never does.
> Turkish grammar hides labels."*

**We deleted this claim.** Two independent problems:

1. **It is not true of our current dataset.** Both languages measure **0.00%**. The
   0.68% came from an older, larger version of the data.
2. **It was never a fair comparison anyway.** Both languages were being checked
   against *English* label names. Of course a Turkish sentence does not contain
   the English word `play_music`. That is not a discovery about Turkish grammar —
   it is a tautology about two different languages.

**Why this is worth showing him:** finding and removing your own wrong claim is a
better sign than never having made one. It was in the README, the datacard, the
design log, the roadmap, and a numbered section of the paper notes. All corrected.

---

## 6. Label noise — now measured, and it found something bigger

**Label noise = how often the "correct answer" in our data is actually wrong.**
It matters because it is the ceiling on any model's score. If 10% of our labels
are wrong, a perfect model still cannot score 100%.

**You annotated 150 rows by hand.** Result:

| | |
|---|---|
| Rows judged | 150 |
| Marked wrong | 14 |
| **Error rate** | **9.3%** (95% confidence: 5.6% – 15.1%) |

**A second review disagreed with 3 of your 14.** For example you flagged *"how
many meetings have there been"* labelled `calendar_query` — but that dataset uses
`calendar_query` for exactly this kind of lookup elsewhere, so it stands.

**So we report a range: 2.7% – 9.3%**, not a single number. The disagreement is
itself part of the result, and hiding it would be dishonest.

### The bigger finding: some of it is bad *translation*, not bad *labelling*

Three of the errors you caught are a different species:

| English original | Turkish as shipped | Label |
|---|---|---|
| *put a record on* | *bir kayıt koy* | `play_music` |
| *how to spell the word treble* | *üç kat kelimesi nasıl kodlanır* | `qa_definition` |
| *when does olive garden close* | *hanım eli bugün ne zaman kapanıyor* | `recommendation_locations` |

**Take the first one.** In English, "put a record on" means *play a vinyl* — so
`play_music` is correct. In Turkish, *kayıt* means a record in the **filing-cabinet**
sense. **No Turkish speaker reads "bir kayıt koy" and thinks about music.**

The idiom was translated word by word, and died.

### Why this is the most important thing in this section

**The English label is right. The Turkish label is wrong. Same record.**

That means the Turkish half of our comparison is being graded against a **noisier
answer key** than the English half — on records that are supposed to be identical.

So any Turkish-vs-English difference we measure is:

> (a real language difference) **+** (translation errors we have not separated out)

**This is a genuine weakness in our headline claim**, and it is now written into
the datacard as a limitation. **Our review datasets are unaffected** — they are
Turkish written by Turkish people, with no translation step to corrupt.

**Fix:** the same 150 rows again, with two columns instead of one — *does the label
fit the English?* and *does it fit the Turkish?* — judged separately. ~30 minutes.

---

## 7. The compatibility tool (`check_pair.py`)

### The problem it solves

Our benchmark works by **pairing** a Turkish dataset with an English one. If
somebody else wants to add a new pair — or another language entirely — how do they
know their two datasets can actually be compared?

Before this, the answer was "read a 60-line document and check eight things by
hand." Now it is one command.

### Using it

```bash
python scripts/check_pair.py configs/musteri_tr.json configs/marc_en.json
```

### What it checks, and why each one matters

| Check | Why | Fails when |
|---|---|---|
| **Label origin** | both sides' labels must be made the same way | one is star ratings, the other is human guesses |
| **Same number of classes** | can't compare 3 categories against 5 | 3 vs 5 |
| **Record length** | changes what "one chunk" means | 14 words vs 72 words |
| **Length spread gap** (§4.7) | lopsided length-cheating breaks the comparison | one side 3.6×, other 1.1× |
| **Class balance** | one class dominating makes guessing easy | 90% positive |
| **Reaches the same sizes** | both must reach 500,000 tokens | small side runs out of data |
| **Brand column on both** | or the two halves ask different questions | one has brands, one doesn't |
| **Licence** ← veto | a better match is worthless if we can't republish it | licence unknown |

### Real output — a pair that works

```
PAIR: musteri_tr (tr, 36,924 rows) <-> marc_en (en, 118,779 rows)

label provenance      ok    both author_stars
label space           ok    both 3 classes
record length         ok    14.3 vs 34.2 words (2.4x)
surface-shape gap     ok    spread 1.19x vs 1.12x  (gap 0.06)
class balance         ok    entropy 1.000 vs 1.000
entity axis           ok    neither -- 6 symmetric families
licence               ok    cc-by-sa-4.0 / apache-2.0

=== COMPATIBLE ===
```

### Real output — a pair with problems

```
record length        warn   14.3 vs 43.0 words (3.0x)
                            -> usable, but state it as a limitation
entity axis          warn   only amazon_hpc_en has one (0 vs 13033)
                            -> the halves would ask different questions
licence              warn   unknown
                            -> text cannot be redistributed

=== COMPATIBLE WITH CAVEATS ===
```

**The verdict has three levels, not two:** `COMPATIBLE`, `COMPATIBLE WITH
CAVEATS`, `INCOMPATIBLE` — because most real pairs are usable *with a stated
limitation*, and a yes/no answer would throw them away.

### The best argument for it

**Run it on our own history and it would have rejected the dataset we deleted —
before we spent weeks building it.**

---

## 8. If we receive new Turkish data, what should we check?

In priority order. The tool checks 1–6 automatically.

1. **Does it have labels?** No labels = unusable, whatever the size. The label is
   the answer key. *(This alone killed a 745,000-article Turkish news corpus.)*
2. **Where did the labels come from?** Best: the writer's own star rating. Worst:
   undocumented. **This is not automatable — someone must read the dataset card.**
3. **Is it big enough?** We need ~40,000+ rows to build million-token documents.
4. **Is the licence clear?** "Unknown" means *no permission*, not *probably fine*.
5. **Is there an English partner** with the same label origin and similar length?
6. **Does length give away the label?** (§4.7)
7. **⭐ Does it have DATES?** — this is the one that would unlock our missing
   question type. Almost nothing Turkish does.

**What we found this week:** we reviewed a fresh list of Turkish datasets. **None
of them beats what we already have.**

- **SentiTurca** — looked promising, but its own documentation says it is three
  datasets we had already evaluated, repackaged. Two of them we had rejected.
- **winvoker** (490,000 rows, the biggest) — rejected. Its card openly states it
  includes *"random text inputs marked as neutral"*. That is a machine assigning
  labels, which is exactly why we deleted our own bad dataset.
- **Interpress news** — **273,000 Turkish news articles WITH REAL DATES,
  2010–2017.** This would close our missing question type. **Blocked on one thing:
  its licence says "unknown".** That needs an email to the publisher — nobody else
  can answer it. Until then it stays blocked and we state it as a limitation.

---

## 9. Real vs synthetic data — would synthetic be better?

Three different things get called "synthetic". They have different answers.

### (a) Artificial *assembly* — what we do. **Correct choice.**

Real reviews, but *we* decide which ones go into each document.

- ✅ **The correct answer is free and exact at any size.** Nobody could hand-count
  "how many negative reviews in this 900,000-token document". We get it for
  nothing, because we assembled it.
- ✅ Length and difficulty become dials we control.
- ❌ It is not a naturally occurring document — no story, no cross-references.

### (b) Synthetic *text* (asking an AI to write fake reviews) — **no.**

- ✅ Unlimited data, no licence problems
- ❌ **It would destroy our main claim.** AI-written Turkish is not Turkish as
  Turkish people write it. Measuring "is Turkish harder for AI" using
  AI-generated Turkish measures the *generator*, not the language.
- ❌ Circular: testing AI on AI-written text.

### (c) Synthetic *labels* (an AI decides positive/negative) — **definitely not.**

The benchmark would measure *agreement with the labelling AI*, not correctness.
And we **deleted a whole dataset** this project because we suspected its labels
were machine-made. We cannot condemn that and then do it ourselves.

**Would synthetic give better numbers? Yes. Better evidence? No.** You would trade
a measurement of real-language ability for a measurement of imitation ability.

**One legitimate use:** as a *control experiment* — e.g. synthetic reviews all the
exact same length, to isolate the length effect from the language effect.

---

## 10. The trajectory dataset — final conclusion

### The idea in one paragraph

When a model solves one of our questions using the RLM method, it leaves a
**trail**: the code it wrote, how it split the document, what it asked itself
about each chunk, and how it added the results up. **We record every trail, keep
only the ones that reached the correct answer, and publish that as a second
dataset** — training material rather than a test.

### What one entry would look like

```
QUESTION  "Bu yorumlardan kaç tanesi 'olumsuz' etiketli?"

STEP 1    chunks = context.split("<<<###>>>")        → 2,847 reviews
STEP 2    for each group of 100, ask a helper:
            "Kaç tanesi olumsuz?"  + [100 Turkish reviews]
            → 41, 38, 44, 29, ...
STEP 3    total = sum(answers)                        → 1,046

GOLD      1,046  ✓   → keep this trail
```

### Is this Turkish-specific, or a general contribution?

**Honestly: mostly general, with a Turkish angle.** We should say both.

| | |
|---|---|
| **General (the bigger contribution)** | Teaching a model *how to break a huge problem into pieces* is language-neutral. That part helps English equally. |
| **Turkish-specific** | The helper calls contain thousands of tokens of **real Turkish**, and the skill of "read this Turkish and classify it under compression" is Turkish-specific. |

So it is **a general RLM contribution with a Turkish component**, and claiming it
is Turkish-only would undersell it while claiming it is Turkish-specific would
oversell it.

### What we could offer that nobody else can

**We can check the model's *working*, not just its final answer.**

Every existing dataset of this kind keeps a trail if the final number was right —
so a lucky guess survives. **We built the document, so we know the label of every
single record.** For any chunk the model picks, we can compute the true answer:

```
model said:  "chunk 12 has 37 negatives"
we know:     chunk 12 (records 2400–2600) has 41
             → that step is wrong by 4, and we can prove it
```

Nobody can do this on real books or papers, because there is no correct answer
below the final one.

### What could a Turkish LLM expect from being trained on it?

**Set expectations low and specific.**

- ❌ **This is NOT Turkish pre-training data.** Those are tens of *billions* of
  tokens. Ours is 28 million, half of it English.
- ✅ **It is fine-tuning data.** The comparable result: RLM-Qwen3-8B gained
  **+28.3%** from just **1,000** trails — an amount we could realistically produce.
- 🎯 **The realistic gain: better at breaking down long Turkish documents.** Not
  "better Turkish".

### Is fine-tuning a Turkish LLM on this unexplored?

**Yes — and honestly so.** Nobody has trained a model on an aggregation benchmark
in *any* language, let alone Turkish. That is a genuine gap.

**But the closest work now exists**, and we must cite it (§11): a 2026 paper does
almost exactly this in English, from Wikipedia tables, and reports **+4.3%**. So:

- The idea is **validated** — it works.
- We are **not first** to the general idea.
- We would be **first in Turkish**, **first from an aggregation benchmark**, and
  **first with verifiable intermediate steps**.
- **Expect gains near +4%, not +28%.**

### The honest objection

OOLONG showed that giving models the correct labels for free helps only 0.79–10.9
points. The bottleneck is not reading — it is **adding thousands of things up**,
which is what a `for` loop does perfectly. So training a model to count in its
head may be optimising the part that should have been replaced by code.

**Our answer:** that objection kills the naive version (train on *question →
answer*) and **strengthens** ours (train on *question → the sequence of moves*).
If the arithmetic should be code, the skill worth learning is **deciding how to
break the problem up** — which is exactly what a trail records.

### Verdict

**Worth doing. Future work, not a promise.** One decision must be taken *now*: the
evaluation harness must **record the trails from the very first run**. That is a
day of engineering. If we skip it, we pay for every experiment twice.

---

## 11. Literature check — anything that changes our direction?

Three findings this week.

**1. OOLONG's construction code is still not released** — this is the claim you
asked me to verify. Their GitHub repo now exists (MIT licence) but contains only
an evaluation script. The pipeline that *builds* the benchmark is explicitly
marked **"coming soon"**. So we still had to rebuild everything from the paper
description, and our independent implementation stands.

**2. ⚠️ Someone has done a close cousin of our trajectory idea** —
*π²: Structure-Originated Reasoning Data* (arXiv:2604.05114, 2026). They generate
reasoning training data from Wikipedia tables, and — strikingly — **verify answers
by two independent code paths, which is exactly our method**. Fine-tuning gives
**+4.3%**. It is English-only, from tables rather than an aggregation benchmark,
and has no verified intermediate steps.

> **Impact on us: it strengthens the case and shrinks the claim.** The approach is
> now published and works, so we no longer have to argue it *might*. But we must
> cite it and stop implying we invented the idea. It also gives us a realistic
> expectation: **+4%, not +28%**.

**3. Still no multilingual OOLONG, and still no Turkish long-context aggregation
benchmark.** I searched again. TurkBench and Cetvel are Turkish but short-context;
OOLONG is English-only. **Our novelty claim holds.**

---

## 12. Where this leaves us — next steps

**Done this week:** the entity bug fixed and rebuilt · the label-vs-label question
type added · `check_pair.py` written and tested · label noise measured · a wrong
claim withdrawn · all five checks green · everything committed and pushed.

**Next, in order:**

1. **Run one small model on a handful of questions.** This is the only real gap.
   It is also the check that would have caught our bug in an hour. *(A first
   attempt is already wired up and revealed a setup bug of its own, now fixed.)*
2. **The 30-minute two-column re-pass** on the same 150 rows, to separate
   translation errors from labelling errors (§6).
3. **Decide: publish the dataset now, or wait for model scores?** My recommendation
   is publish now — it timestamps the work and costs nothing.
4. **Optional:** email Interpress about their licence, which would unlock the
   missing date questions (§8).

**What we do NOT need: more data.** We looked, and nothing available beats what we
have.
