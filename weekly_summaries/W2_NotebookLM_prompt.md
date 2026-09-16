# NotebookLM prompt — Week 2 **progress** slides

**How to use:** upload `W2_Summary.md` to NotebookLM as a source, then paste the
block below.

**What this produces:** a deck about **what I did this week** — the problems I
found, what I fixed, what I decided. Not an introduction to the project. One
slide of context, then the week's work.

---

```
Create a slide deck reporting ONE WEEK OF PROGRESS on a research project.

WHAT THIS DECK IS
This is a weekly progress report, like a work update to a manager. It is NOT an
introduction to the project. Do not spend slides explaining what the project is,
why it matters, or how it works in general. Give that exactly ONE slide of
background at the start, then spend every other slide on WHAT HAPPENED THIS WEEK:
what I looked into, what I discovered, what I fixed, what I decided, what I got
wrong.

AUDIENCE
One English language teacher. No background in computer science, artificial
intelligence, or statistics. Assume they have never heard of a "language model",
a "dataset", or a "benchmark". They are intelligent and curious, and they are
interested in LANGUAGE — so lean into anything about Turkish versus English,
because that is what they will connect with.

MY ROLE
I am presenting and I do all the talking. Each slide must give me roughly two
minutes of material to speak about. The bullets are prompts for ME to expand on,
not sentences to read aloud. If a slide can be read out word for word, it has too
much text.

FORMAT
- 12 slides.
- Each slide: a title, 3 to 5 bullets, and one concrete example.
- Each bullet: 12 words maximum. Fragments, not sentences.
- The example may be longer, and should be specific: a real number, a real
  question, a real sentence.
- No paragraphs anywhere. No speaker notes.

BANNED WORDS, and what to say instead:
    tokenizer          -> "the software that counts text"
    token              -> "unit of text"
    dataset / corpus   -> "collection of reviews"
    annotation         -> "labelling"
    aggregation        -> "counting across everything"
    entity             -> "brand"
    label              -> "tag" or "category"
    benchmark          -> "test" or "exam"
    model              -> "AI system"
    query / parse      -> "ask" / "read"
No formulas, no statistics notation, no percentage ranges.

THE TWELVE SLIDES

1.  ONE slide of background only. What the project is: an exam that is
    deliberately very hard for AI systems. Example: glue 3,000 real Turkish
    product reviews into one huge document, then ask "how many of these are
    negative?" — answer 1,046. Searching does not help; you must read them all.

2.  What I set out to do this week: check the work for mistakes before publishing
    it, and answer a list of questions from my supervisor.

3.  THE BIG PROBLEM I FOUND. Some questions asked about brands, but I had never
    printed the brand names into the document. Example: the question asked how
    many "Venatura" reviews were neutral — the answer is 10 — but the word
    "Venatura" appeared ZERO times in the text. Nobody could have answered it.
    That was 118 questions, about one in ten.

4.  Why my safety checks did not catch it. I had four automatic checks, all
    asking "is this question TOO EASY?". None asked "can this be answered AT
    ALL?". Analogy: four anti-cheating systems for an exam, and nobody checked
    the exam had answers.

5.  How I fixed it, and the safeguard. Brand names now appear in the text, and
    the system now REFUSES to build a test that asks about brands without showing
    them. The mistake cannot happen silently again.

6.  A missing feature I added. The English test we are based on could ask "are
    there more of category A or category B?" — mine could not. I added it. I also
    had to fix a fairness problem: at first the answer was "more" far too often,
    so a lazy system could score well by always guessing "more".

7.  Checking the data by hand. I read 150 Turkish sentences one by one and judged
    whether each was labelled correctly. Result: about 9 in 100 were wrong. I
    also built a small tool so the checking could be done without a spreadsheet.

8.  WHAT THAT REVEALED — the most interesting discovery of the week. Some errors
    were not bad labelling, they were bad TRANSLATION. Example: "put a record on"
    in English means "play some music". The Turkish translation came out meaning
    "place a document in a filing cabinet". The tag still said "music", but the
    Turkish no longer did.

9.  Why that discovery matters, and why it is uncomfortable. The English side is
    correct and the Turkish side is wrong, on sentences that are supposed to be
    identical. So the Turkish half is being marked against a worse answer key.
    That weakens my main comparison, and I wrote it down as a known weakness
    instead of hiding it.

10. A claim I deleted. I had written in five documents that Turkish grammar hides
    information in a way English does not. I checked, and it was not true of my
    current data — and the comparison had been unfair anyway. I removed it
    everywhere. Finding your own mistake is a good sign, not a bad one.

11. A LANGUAGE finding. The same Turkish sentence costs different amounts of
    "text units" depending on whose software counts it. Example: the same 3,000
    sentences make Turkish 34% longer than English under one company's counter,
    but only 22% under another's — and under a Turkish-made one, Turkish comes
    out SHORTER. So "Turkish is a longer language" is partly about the ruler, not
    the language.

12. Where things stand, and next week. The work is published and all checks pass.
    Everything is ready except one thing: no AI system has actually taken the
    exam yet. That needs a powerful computer I do not have access to yet.

TONE
Confident, plain, factual. This was a productive week that included finding two
of my own mistakes and fixing them. Do not oversell, do not apologise, and do not
use marketing language.

OUTPUT
For each slide give me only: the title, the bullets, and the example.
```

---

## Follow-ups if the first attempt is off

**It drifted back into explaining the project:**

```
Slides [N] and [M] explain the project instead of reporting this week's work.
Replace them with things that happened this week: a problem found, a fix made,
a decision taken, or a discovery.
```

**Not enough for me to talk about:**

```
Each slide needs about two minutes of speaking material. Add one more bullet to
each slide giving me an angle to expand on — a consequence, a comparison, or
what I would do differently.
```

**Too wordy:**

```
Cut every bullet to 12 words or fewer. Delete anything I could say out loud
instead. Keep the examples.
```

**If you are short on time:**

```
Cut to 8 slides. Priority: 1, 3, 4, 5, 8, 9, 11, 12.
```
