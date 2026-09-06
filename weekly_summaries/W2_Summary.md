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

### 4.3 The tokenizer — we used Qwen. Should we use GPT's or Claude's? Can we be attacked on this?

A **tokenizer** chops text into the pieces a model actually counts and charges
for. Different models chop differently.

**Two separate uses, and only one of them is risky.**

**(a) As a ruler, to say "this document is 100,000 tokens" — completely fine.**
You need *one* consistent ruler, and Qwen is the model family we plan to test.
Any consistent ruler would do.

**(b) As evidence that "Turkish costs more tokens than English" — this is where a
reviewer could attack, and they would be right to.** On the *exact same 3,000
sentence pairs*, measured this week:

| Tokenizer | Used by | Turkish costs |
|---|---|---|
| `p50k_base` | GPT-3 era | **2.16×** English |
| `cl100k_base` | GPT-3.5 / GPT-4 | **1.73×** |
| `o200k_base` | **GPT-4o / GPT-5 era** | **1.35×** |
| Qwen3-8B | Qwen (**ours**) | 1.53× |
| mBERT | multilingual BERT | 1.29× |
| **BERTurk** | Turkish-specific | **0.57× — Turkish is CHEAPER** |

**Look at the top three rows — that is a clear trend over time.** As OpenAI's
tokenizers got newer, the Turkish penalty fell from 2.16× to 1.35×. Newer
tokenizers were trained on more non-English text. **That is strong evidence the
number measures the tokenizer's training diet, not Turkish grammar.**

#### Why didn't we use GPT's or Claude's tokenizer?

| | Available? | Cost | Could we build with it? |
|---|---|---|---|
| **OpenAI (`tiktoken`)** | ✅ Open source | **Free**, works offline | **Yes** — we just did, for the table above |
| **Claude** | ❌ **Not published** | Free API endpoint, but needs a key and internet per call | **No** — it would make our build non-reproducible offline |
| **Qwen** (ours) | ✅ Open | Free, offline | Yes |

**So it is not about money.** OpenAI's is free and we used it. Claude's tokenizer
is simply not public — Anthropic only offers a counting endpoint over the network,
and building a benchmark that phones a company's server to measure itself would
make it unreproducible.

**We chose Qwen because it is the model family the experiments will actually run
on**, and it is open and offline.

#### Would OpenAI's tokenizer make our dataset longer or shorter?

**Measured on our actual documents — the answer differs for the two languages, and
that is the interesting part.**

The same document, counted twice:

| Document | Qwen (what we built with) | OpenAI `o200k_base` | Change |
|---|---|---|---|
| Turkish, 100K tier | 99,266 tokens | **89,178** | **−10%** |
| English, 100K tier | 98,246 tokens | **96,477** | **−2%** |

**So OpenAI's tokenizer counts the same text as SHORTER — and it shortens Turkish
about five times more than English.**

Two consequences, depending on what you do with it:

1. **If we only re-label the existing documents**, our "100,000-token" Turkish
   document becomes a "89,000-token" document. **Same text, smaller number.**
2. **If we rebuilt to the same 100,000-token target**, the builder would pack in
   **~10% more Turkish reviews** before hitting the limit. **Same number, more
   content** — and a genuinely harder task, because there is more to count.

**And it changes the headline number.** On the record-matched pair — the *same
3,000 sentences* in both languages:

| Tokenizer | Turkish costs |
|---|---|
| Qwen3-8B (ours) | **1.34×** English |
| OpenAI `o200k_base` | **1.22×** English |

**This is the cleanest demonstration of the whole point.** Identical sentences,
identical content, and the "Turkish penalty" moves from 34% to 22% purely by
changing which company's tokenizer you count with. It is a property of the
measuring instrument, not of Turkish.

#### Could a jury attack us? Yes — here is the defence

**The attack:** *"Your headline 'Turkish costs 1.3× more tokens' is an artifact of
picking one tokenizer."*

**Four answers, in order of strength:**

1. **We say so ourselves, and we publish the whole spread** (the table above). We
   are not hiding it — we are reporting it as a finding.
2. **We record the character count of every document**, so anyone can re-derive
   sizes under their own tokenizer without rebuilding anything.
3. **Our strongest comparison has no tokenizer involvement at all.** The
   record-matched pair (§4.5, Version 2) uses the *same sentences* in both
   languages. There is no token budget to bias.
4. **The generational trend is itself the result.** "The Turkish token penalty
   halved between GPT-3 and GPT-5 tokenizers" is a cleaner, more interesting
   claim than any single number.

**Turning the weakness into the finding is the right move here**, and it is what
we now do.

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

### 4.5 `tr_intent` vs `tr_intent_paired` — the clearest way to see it

**Start from what makes this data special.** The MASSIVE dataset contains the
*same sentences* in Turkish and English. Sentence #4021 is:

> Turkish: *"beni cuma günü sabah dokuzda uyandır"*
> English: *"wake me up at nine am on friday"*

Same meaning, same label (`alarm_set`). This lets us ask an identical question in
both languages — but only if we build the documents carefully. There are two ways
to do it, and they answer different questions.

#### Version 1 — `tr_intent` / `en_intent`: **same size**

> **Rule: fill both documents to exactly 100,000 tokens.**

Turkish words cost more tokens than English ones, so at the same size the Turkish
document **runs out of room sooner** and holds fewer sentences:

| | Turkish doc | English doc |
|---|---|---|
| Size | 100,000 tokens | 100,000 tokens |
| **Sentences that fit** | **6,169** | **8,122** |
| Correct answer to *"how many are `alarm_set`?"* | 122 | 161 |

**The two answers are different, and that is correct** — they are different piles
of sentences. This version asks: *"given the same budget, which language is
harder?"*

#### Version 2 — `tr_intent_paired` / `en_intent_paired`: **same content**

> **Rule: use exactly these 3,000 sentences, in this order, in both languages.**

Now the documents hold **the same sentences**, so the Turkish one is simply
**longer** in tokens:

| | Turkish doc | English doc |
|---|---|---|
| Sentences | **3,000 — the same ones** | **3,000 — the same ones** |
| Size | 99,057 tokens | 75,187 tokens |
| Correct answer to *"how many are `transport_taxi`?"* | **18** | **18** |

**Same question, same answer, different language.** So if a model scores 18 on
English and 12 on Turkish, that gap **is** the language. Nothing else changed.

#### The analogy that makes it click

> Two students, one reading Turkish, one reading English.
>
> - **Version 1** gives each of them **300 pages**. But the Turkish book is
>   printed in bigger type, so the Turkish student gets through **fewer chapters**.
> - **Version 2** gives each of them **the same 20 chapters**. The Turkish book is
>   simply a **thicker book**.
>
> Version 1 asks *"who does more with the same reading time?"*
> Version 2 asks *"who understands the same material better?"*

**Only Version 2 lets us make the strong claim**, because only there is the
correct answer identical. **100 of its 120 questions have the same answer in both
languages.** We ship both because they are genuinely different questions.

### 4.5b Have we translated the labels and brands into Turkish?

**Partly — and the answer is different for each of the three things.**

| | Translated? | Why |
|---|---|---|
| **Review labels** | ✅ **Already Turkish** — `olumlu` / `olumsuz` / `nötr` | They come from star ratings, and we chose the words. The English twin uses `positive` / `negative` / `neutral` |
| **Intent labels** | ❌ **Still English** — `transport_taxi` in both languages | These are database codes from the original dataset, not words. §4.6 is about whether to change this |
| **Brand names** | ❌ **Never** — `Nutraxin`, `Balen`, `Nbt İlaç` | They are proper nouns. Translating a brand would be wrong, not helpful |

**So: 4 of our 8 sets already have Turkish labels.** The only open question is the
intent sets, which is exactly §4.6 below. **We have not done that translation** —
it is an experiment we have measured the cost of, not a change we have made.

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

| Check | What it means | ✅ Passes | ❌ Fails |
|---|---|---|---|
| **Label origin** | both sides' labels must be produced the same way | TR = customer's own stars, EN = customer's own stars | TR = customer's stars, EN = strangers guessing the mood |
| **Number of classes** | you cannot compare 3 buckets against 5 | both have 3 (`olumlu`/`olumsuz`/`nötr` ↔ `positive`/`negative`/`neutral`) | TR has 3, EN has 5 (1–5 stars kept separate) |
| **Record length** | changes what "one chunk" means for the model | 14 words vs 34 words (2.4×) | 13 words vs 72 words (5.4×) — this killed a real candidate |
| **Length spread gap** (§4.7) | one-sided length-cheating fakes the comparison | TR 1.19× and EN 1.12× → gap 0.06 | TR 3.6× and EN 1.4× → the model reads English but measures Turkish |
| **Class balance** | one dominant class makes guessing easy | 33% / 33% / 33% on both sides | 90% positive — always answer "positive", score 90% |
| **Reaches the same sizes** | both halves must build the same length documents | both reach 500,000 tokens | TR runs out at 200,000 — no comparison above that |
| **Brand column on both** | or the halves ask different questions | neither has brands → both ask the same 6 question types | EN has 13,033 brands, TR has 0 → EN gets 9 types, TR gets 6 |
| **Licence** ← **veto** | a better match is worthless if we cannot republish it | `cc-by-sa-4.0` ↔ `apache-2.0` | `unknown` — which means *no permission*, not *probably fine* |

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

### What one row of the dataset would actually look like

Think of it as a table where **each row is one complete solved problem**. Here is
one row written out in full:

```json
{
  "question":  "Bu yorumlardan kaç tanesi 'olumsuz' etiketli?",
  "language":  "tr",
  "gold":      1046,

  "steps": [
    { "n": 1,
      "code":   "chunks = context.split('<<<###>>>')",
      "output": "2847",
      "correct": true },

    { "n": 2,
      "code":   "counts = [ask_helper('Kaç tanesi olumsuz?', c) for c in groups]",
      "output": "[41, 38, 44, 29, ...]",
      "correct": true,
      "we_can_verify": "group 1 truly contains 41 → step is right" },

    { "n": 3,
      "code":   "answer = sum(counts)",
      "output": "1046",
      "correct": true }
  ],

  "final_answer": 1046,
  "kept": true
}
```

**How to read that:**

- `question` + `gold` — the input and the known correct answer
- `steps` — **the model's working**, in order
- `final_answer` — what it concluded
- `kept: true` — it matched the gold answer, so this row goes in the dataset

### What is the training target?

**This is the key design choice, and it is not obvious.**

| Bad target | Good target |
|---|---|
| `question → 1046` | `question → the list of steps` |
| Teaches the model to **guess a number** | Teaches the model to **plan a method** |

A model trained on the left learns to blurt out a plausible-looking number. A
model trained on the right learns *"first split the document, then ask about each
piece, then add it up"* — a habit that transfers to problems it has never seen.

**Concretely, the model is trained to produce the `steps` field**, given the
question. The final number is just how we decide whether to keep the row.

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

**2. ⚠️ Someone has done a close cousin of our trajectory idea.**
*π²: Structure-Originated Reasoning Data Improves Long-Context Reasoning*
(arXiv:2604.05114, 2026). **This is the most relevant new paper for us and we must
cite it.**

**What they did**, in plain terms:

1. They took **Wikipedia tables** — structured data where the facts are already
   organised in rows and columns.
2. They **generated hard questions** from those tables automatically — questions
   needing several steps, like *"which country in this table had the biggest
   increase between 2010 and 2015?"*
3. They **checked every answer by running code two separate ways** and confirming
   the two agreed.
4. They wrote out **step-by-step solutions**, and fine-tuned models on those.
5. Result: **+4.3% and +2.7%** on long-context reasoning benchmarks.

**Why this matters so much to us — the overlap is uncomfortably close:**

| | π² (them) | TR-OOLONG (us) |
|---|---|---|
| Source of correct answers | structured Wikipedia tables | labelled review datasets |
| How answers are verified | **two independent code paths** | **two independent code paths** ← identical idea |
| What they train on | step-by-step solutions | the trail of steps (§10) |
| Language | **English only** | **Turkish + matched English** |
| Verified *intermediate* steps | ❌ final answer only | ✅ we know every record's label |
| Comes from a benchmark | ❌ built for training | ✅ ours is an evaluation set first |

> **What this changes for us — three things, and we should say all of them:**
>
> 1. **It validates the approach.** We no longer have to argue this *might* work.
>    It is published and it works.
> 2. **It shrinks our claim.** We are not first to the general idea, and we must
>    stop writing as if we were. We are first *in Turkish*, first *from an
>    aggregation benchmark*, and first *with checkable intermediate steps*.
> 3. **It sets a realistic expectation: around +4%, not +28%.** The +28.3% figure
>    from RLM-Qwen3-8B came from a different kind of training. Promising +28%
>    would be overselling.

**3. Still no multilingual OOLONG, and still no Turkish long-context aggregation
benchmark.** I searched again. TurkBench and Cetvel are Turkish but short-context;
OOLONG is English-only. **Our novelty claim holds.**

---

## 11b. One observation from the first trial run — worth watching, NOT a finding

We wired up a first trial run (§15, step 1). It timed out before finishing, but
the log of what the model *tried* contained something we should keep an eye on.

**The model was given the same question in both languages, and approached them
differently.**

| | What it did |
|---|---|
| **English** | Split the document into utterances, then: *"Since the intent isn't explicitly labeled in the text, I will use a sub-model to classify each utterance."* → **the intended method** |
| **Turkish** | Ran `context.count('transport_taxi')` — **counting how many times the label appears as a literal string** — then went hunting for that string inside each record |

**In plain terms: on English it reasoned "I'll have to read these and judge them".
On Turkish it first tried to just search for the answer.**

**Our benchmark blocked the shortcut**, exactly as designed — no record contains a
label word, so the search returned nothing and the model had to move on.

### Why this is interesting if it holds up

Our whole grep-proofness design exists to stop a model answering by string
matching instead of reading. If models reach for that shortcut **more readily in
languages they are weaker at**, that is:

- a real phenomenon worth publishing,
- directly relevant to why this benchmark exists,
- and something only a matched-twin design like ours can even detect.

### Why we must NOT claim it yet — three serious problems

1. **n = 1.** One run per language. This could be pure chance.
2. **Our own bug invited it.** In that run the question text was accidentally
   glued into the document — and the question *contains* the string
   `'transport_taxi'`. So the model had a reason to search that it would not have
   in a correct run. That bug is now fixed.
3. **The two runs never reached the same stage.** Turkish got 4 steps in before
   timing out; English only got 2. English may simply not have reached the point
   where it would have tried the same thing.

**Status: a hypothesis to test, written down so we do not forget it.** The clean
version is easy — same question, both languages, correct harness, several
repetitions, and count how often each language reaches for string matching before
classification.

---

## 12. How do we stop a model just guessing?

**We thought about this a lot — it is the single biggest threat to a benchmark
like ours.** If a question can be answered without reading, the benchmark measures
nothing. Five defences, each added because an earlier version failed:

### 1. The answer is never written in the text

The label (`olumsuz`) must be *worked out*. Any review that literally contains a
label word is **deleted before we build**.

> **Why:** an early version had a program that did nothing but search for three
> Turkish words. It got `most_common` right **73% of the time** (chance: 33%). Only
> **0.84%** of records leaked — and that was enough. *Leak rate is not the same as
> exploitability.*

### 2. We name the options, then make them equally likely

Every ranking question lists its candidates:

> *"Which brand got the most positive reviews: Beeo, NBL, Nbt İlaç, Smartcaps,
> Suda Collagen?"*

The five are chosen to have **near-identical counts in the source data**, so the
biggest brand overall is not automatically the answer.

> **Why:** before this, **every single** `pairwise` question on one set was
> answerable **with no document at all** — just by knowing which brand is more
> popular in general. And it got *worse* with longer documents.

### 3. We check "always answer the most common thing"

For every question type we compute what a model scores by ignoring the document
and always giving the most frequent answer. If that scores well, the type is
broken.

> **Why:** one question type had a "just guess" score of **1.00** — a rare label
> was the correct answer in **10 out of 10** documents.

### 4. We reject questions that are too close to call

If the top two options differ by less than 10%, we **throw the question away**
rather than ship a coin flip.

> Also: we count how many records decide the answer. One question rested on
> **8 records out of 3,919**. Deleted.

### 5. Four "cheating programs" must all fail before we ship

| Program | Cheats by |
|---|---|
| Word search | looking for label words |
| Always-the-same-answer | ignoring the document |
| Statistics-only | using general facts, never opening the document |
| Length-and-punctuation | measuring sentences, reading nothing (§4.8) |

**All four must fail.** Their results are published with the dataset as evidence.

### And the honest gap

**These all test "is it too easy". Until this week, nothing tested "is it possible
at all"** — which is exactly how the brand bug (§1) survived. That check is now a
build-time rule, and running a real model is the last piece.

---

## 13. What else could still be analysed?

Nothing here blocks publication. These are the questions a thorough reviewer might
ask that we have not yet answered.

| Analysis | Why it would help | Effort |
|---|---|---|
| **Split translation errors from labelling errors** (§6) | our one measured weakness; would turn a confound into a number | 30 min (you) |
| **Does difficulty actually rise with length?** | we assume 900K is harder than 100K; never measured | needs model runs |
| **Per-question-type difficulty** | which of the 10 types is hardest? Currently unknown | needs model runs |
| **Documents in the same size tier share 21–39% of their records** | means confidence intervals need a statistical correction; currently noted but not applied | half a day |
| **Is `shift` salvageable?** | it is our weakest type; maybe a different threshold helps | half a day |
| **Human baseline on 20 questions** | "can a person even do this?" is a question reviewers love | ~2 hours |
| **5 classes instead of 3 on the review sets** | we merge 1–5 stars into 3 buckets; keeping 5 would make guessing harder | 1 hour |

**The middle two need a model.** That is the theme of everything below.

---

## 14. Blockers — what is actually stopping us

**Be precise here, because "blocker" is being used for three different things.**

| | Blocks what? | Blocked by | In our control? |
|---|---|---|---|
| **No model has been run** | the **paper** — not the dataset | GPU access | ⏳ waiting |
| **Translation vs labelling errors unsplit** | a clean cross-lingual claim | 30 min of annotation | ✅ **yes** |
| **No date questions** | closing our one structural gap | Interpress licence answer | ❌ **needs an email** |
| **Brand questions rest on one Turkish dataset** | breadth, not correctness | no other Turkish source has a usable brand column | ❌ state as limitation |

**Nothing blocks releasing the dataset.** One item blocks the paper, and it is
compute, not correctness.

---

## 15. Where this leaves us — next steps

**Done this week:** the entity bug fixed and rebuilt · the label-vs-label question
type added · `check_pair.py` written and tested · label noise measured · a wrong
claim withdrawn · all five checks green · everything committed and pushed.

**Next, in order:**

| # | Step | Who | Unblocks |
|---|---|---|---|
| **1** | **Run one small model on a few questions** | needs a GPU or an API key | the paper. It is also the check that would have caught our bug in an hour *(already wired up; a first attempt found a setup bug of its own, now fixed)* |
| **2** | **The 30-minute two-column re-pass** (§6) | **you** | our one measured weakness |
| **3** | **Decide: release the dataset now?** | **you** | my recommendation is **yes** — it timestamps the work and costs nothing |
| **4** | Email Interpress about their licence (§8) | **you** | the missing date questions — optional |

**What we do NOT need: more data.** We reviewed a fresh list this week and nothing
available beats what we already have (§8).

**One thing worth repeating:** steps 2, 3 and 4 are all yours and none needs a
GPU. Step 1 is the only one waiting on hardware.
