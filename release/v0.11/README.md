# TR-OOLONG v0.11 (provisional, data only)

The v0.11 data is on Hugging Face:
[yigitates17/tr-oolong](https://huggingface.co/datasets/yigitates17/tr-oolong)
(tag `v0.11.0-provisional`). This folder holds the files needed to check it
without downloading the documentation from there:

- `CONSTRUCTION.md`: how documents, questions and answers are built.
- `label_maps.json`: source label to released label, per set.
- `provenance.json`: sources, pinned revisions, source-file hashes,
  tokenizer, seeds.
- `recompute_answers.py`: recomputes every answer from the labelled records
  (Python standard library only) and restores the text of the two sets that
  ship without it.
- `restore_hints.json`: which source line to use for 5 texts that occur
  more than once with different ratings.
- `SHA256SUMS`: the hash of every file in the Hugging Face release.

**Code.** v0.11 was built with an adapted version of the OOLONG-synth
generator. The generation code will be published here together with the
paper. The code elsewhere in this repository
builds v0.10 and is not the v0.11 generator.

**Licences.** Each set keeps its source's licence (dataset card). The text of
`marc_en` and `amazon_hpc_en` is not distributed; from v0.11 this includes
MARC, whose terms do not allow republication.
