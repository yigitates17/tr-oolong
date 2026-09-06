# NotebookLM prompt — Week 2 slides for a non-technical audience

**How to use:** upload `W2_Summary.md` to NotebookLM as a source, then paste
everything in the box below as your prompt.

---

```
Create a short slide deck from the attached document.

AUDIENCE
The audience is one person: an English language teacher with no background in
computer science, artificial intelligence, or statistics. Assume they have never
heard of a "language model", a "dataset", or a "benchmark". They are intelligent
and curious, but every technical term is new to them.

MY ROLE
I am the presenter and I will do all the talking. The slides are only my anchor
points. Do NOT write out explanations, paragraphs, or speaker notes that say the
same thing I would say out loud. If a slide can be read aloud word for word, it
has too much text on it.

FORMAT RULES
- 10 to 12 slides maximum.
- Each slide: one clear title, and 3 to 5 short bullet points.
- Each bullet: 12 words maximum. Fragments are better than sentences.
- No paragraphs anywhere.
- Every slide that introduces an idea must include ONE concrete example, clearly
  marked as an example. The example may be longer than 12 words.
- Use plain English. If a technical word is unavoidable, put a 5-word plain
  definition in brackets right after it the first time.
- No jargon: avoid "tokenizer", "corpus", "annotation", "provenance",
  "aggregation", "entity", "epsilon", "construct validity". Use everyday words
  instead: "text", "collection", "labelling", "where the data came from",
  "counting", "brand", "error rate", "is the test fair".
- No statistics notation, no percentages with confidence intervals, no formulas.

WHAT THE DECK SHOULD COVER, IN THIS ORDER
1.  What the project is, in everyday terms. Use an analogy: we are writing an
    exam that is very hard for computers to pass.
2.  Why Turkish. What is missing in the world right now.
3.  How the test works. Use the example of reading thousands of product reviews
    and counting how many are negative — a person could do it but it would take
    hours; we are testing whether a computer can.
4.  Why searching does not help. The answer is not written anywhere in the text;
    you must read every single item.
5.  The mistake we found this week, and why it matters. We asked questions about
    brands, but we had forgotten to print the brand names into the text — so the
    questions were impossible to answer. Explain that our four automatic checks
    all tested whether the exam was TOO EASY, and none tested whether it could be
    answered at all.
6.  How we fixed it, and the safeguard that stops it happening again.
7.  A second discovery: some of our Turkish came from translated English, and
    some idioms broke in translation. Use the "put a record on" example — in
    English it means play music; the Turkish translation means place a document
    in a filing cabinet.
8.  A claim we deleted because we found out it was wrong, and why admitting that
    is a good sign rather than a bad one.
9.  A tool we built so other people can check whether their own two collections
    of text can be fairly compared.
10. Where the project stands now, and what happens next.

TONE
Confident and plain. This is a progress report on real work with real results,
including one real mistake that we found ourselves and fixed. Do not oversell,
do not apologise, and do not use marketing language.

OUTPUT
Plain text or markdown. For each slide give me: the slide title, the bullet
points, and the example. Nothing else.
```

---

## If the first result is too wordy

Paste this as a follow-up:

```
Too much text. Cut every bullet to 12 words or fewer, delete any bullet that
explains something I could say out loud instead, and keep only the examples.
```

## If it uses jargon anyway

```
Slide [N] uses words my audience will not know. Rewrite it using only everyday
English, and add one concrete example to make the idea land.
```
