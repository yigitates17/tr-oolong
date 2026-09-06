# NotebookLM prompt — Week 2 slides for a non-technical audience

**How to use:** upload `W2_Summary.md` to NotebookLM as a source, then paste
everything in the box below as your prompt.

**Audience assumed:** one English language teacher, no AI background. You present;
the slides only anchor you.

---

```
Create a short slide deck from the attached document.

AUDIENCE
The audience is one person: an English language teacher with no background in
computer science, artificial intelligence, or statistics. Assume they have never
heard of a "language model", a "dataset", or a "benchmark". They are intelligent
and curious, and they are interested in LANGUAGE — so where a point touches on
Turkish vs English, lean into that, because it is the part they will connect with.

MY ROLE
I am the presenter and I will do all the talking. The slides are only my anchor
points. Do NOT write explanations, paragraphs, or speaker notes that say what I
would say out loud. If a slide can be read aloud word for word, it has too much
text on it.

FORMAT RULES
- 12 slides maximum.
- Each slide: one clear title, and 3 to 5 short bullet points.
- Each bullet: 12 words maximum. Fragments are better than sentences.
- No paragraphs anywhere.
- Every slide that introduces an idea must include ONE concrete example, clearly
  marked as an example. The example may exceed 12 words.
- Plain English. If a technical word is unavoidable, put a 5-word plain
  definition in brackets after it the first time.
- BANNED WORDS, with what to use instead:
    tokenizer          -> "the software that counts text"
    token              -> "unit of text"
    corpus / dataset   -> "collection of reviews"
    annotation         -> "labelling"
    provenance         -> "where the labels came from"
    aggregation        -> "counting across everything"
    entity             -> "brand"
    label              -> "tag" or "category"
    benchmark          -> "test" or "exam"
    model              -> "AI system"
    epsilon / CI       -> "error rate", no ranges
- No formulas, no statistical notation, no confidence intervals.

WHAT THE DECK SHOULD COVER, IN THIS ORDER

1.  What the project is. Analogy: we are writing an exam that is deliberately
    very hard for AI systems to pass.

2.  Why Turkish. Nobody had built this. The closest existing test covers 26
    languages and Turkish is not one of them.

3.  How the test works. Example: glue together 3,000 real Turkish product
    reviews, then ask "how many of these are negative?" — answer 1,046. A person
    could do it, but it would take hours.

4.  Why searching does not help. The answer is not written anywhere in the text.
    You must read every single review and judge each one.

5.  Where the correct answers come from, and why this is the clever part. Every
    review already carries the star rating its own author gave it. So nobody has
    to write an answer key by hand — which is the only reason this can work at
    this size.

6.  The mistake we found this week. We asked questions about brands, but had
    forgotten to print the brand names into the text. Example: the question asked
    how many "Venatura" reviews were neutral — answer 10 — but the word
    "Venatura" appeared ZERO times in the document. Nobody could have answered.

7.  Why our automatic checks missed it. We had four systems checking whether the
    exam was TOO EASY. None of them checked whether the questions could be
    answered at all. Analogy: four anti-cheating systems, and nobody checked the
    exam had answers.

8.  How we fixed it, plus the safeguard: the system now refuses to build a test
    that asks about brands without showing them.

9.  A LANGUAGE finding the audience will enjoy. The same Turkish sentence costs
    different amounts of "text units" depending on whose software counts it.
    Example: the same 3,000 sentences make Turkish 34% longer than English under
    one company's counter, but only 22% longer under another's. So "Turkish is a
    longer language" turns out to be partly about the measuring tool, not the
    language.

10. A translation discovery. Some of our Turkish came from translated English,
    and idioms broke in translation. Example: "put a record on" means "play some
    music" in English; the Turkish translation came out meaning "place a document
    in a filing cabinet". The label said "music" but the Turkish no longer did.

11. A claim we deleted because we discovered it was wrong — and why finding your
    own mistake is a good sign, not a bad one.

12. Where the project stands, and what happens next.

TONE
Confident and plain. This is a progress report on real work, including two real
mistakes that we found ourselves and fixed. Do not oversell, do not apologise,
do not use marketing language.

OUTPUT
For each slide give me only: the slide title, the bullet points, and the example.
Nothing else.
```

---

## Follow-up prompts, if the first attempt is off

**Too wordy:**

```
Too much text. Cut every bullet to 12 words or fewer, delete any bullet that
explains something I could say out loud instead, and keep the examples.
```

**Still using jargon:**

```
Slide [N] uses words my audience will not know. Rewrite it in everyday English
and add one concrete example.
```

**Not enough examples:**

```
Slides [N] and [M] state an idea without showing one. Add a specific example to
each — a real question, a real number, or a real sentence.
```

**If you want a shorter version for time:**

```
Cut this to 8 slides. Keep slides 1, 3, 6, 7, 9, 10 and 12 as the priority, and
merge the rest.
```
