"""Golden-file regression test for the TR-OOLONG builder.

Rebuilds a tiny committed fixture and byte-compares the output against the
committed golden files. Any change to sampling, ordering, question generation,
or ground truth fails this test; intentional changes require --regen plus a
VERSION bump in src/build_tr_oolong.py.

Usage:
    python tests/test_golden.py            # verify (exit 0 = pass)
    python tests/test_golden.py --regen    # rewrite the golden files
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_tr_oolong as b

GOLDEN = ROOT / "tests" / "golden"
CONFIG = ROOT / "tests" / "fixture_config.json"
FILES = ("questions.jsonl", "haystacks.jsonl")


def normalized_manifest(path: Path) -> dict:
    man = json.loads(path.read_text(encoding="utf-8"))
    man["date"] = None
    man["environment"] = None
    man["config"]["out_dir"] = None
    return man


def build_to(out_dir: Path) -> None:
    cfg = b.Config.load(str(CONFIG))
    cfg.source_path = str(ROOT / "tests" / "fixture_source.csv")
    cfg.out_dir = str(out_dir)
    b.build(cfg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regen", action="store_true")
    args = ap.parse_args()

    if args.regen:
        if GOLDEN.exists():
            shutil.rmtree(GOLDEN)
        GOLDEN.mkdir(parents=True)
        build_to(GOLDEN)
        for p in GOLDEN.glob("meta_*.parquet"):
            p.unlink()                      # jsonl + manifest are the contract
        print(f"golden files regenerated -> {GOLDEN}")
        return

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        build_to(out)
        failures = []
        for name in FILES:
            if (out / name).read_bytes() != (GOLDEN / name).read_bytes():
                failures.append(name)
        if normalized_manifest(out / "manifest.json") != normalized_manifest(GOLDEN / "manifest.json"):
            failures.append("manifest.json")
        if failures:
            print(f"GOLDEN TEST FAILED: {failures} differ from tests/golden/")
            print("If the change is intentional: bump VERSION and rerun with --regen.")
            sys.exit(1)
        print("GOLDEN TEST PASSED: rebuild is byte-identical to tests/golden/")


if __name__ == "__main__":
    main()