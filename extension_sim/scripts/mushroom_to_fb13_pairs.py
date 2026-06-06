#!/usr/bin/env python3
"""
Convert mushroom Freebase13 → extension_sim/data/fb13_pairs.tsv

Mushroom repo: https://github.com/gnodisnait/mushroom
Figshare zip:  https://ndownloader.figshare.com/files/13548377

Train/valid lines:  HEAD TAIL REL   (3 fields, all positive)
Test lines:         HEAD TAIL REL LABEL   (LABEL: True/False or 1/-1)

Output TSV (no header): head \\t relation \\t tail \\t label
  label 1 = correct, 0 = incorrect
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "fb13_pairs.tsv"

# Also check repo-root data/ (sibling of extension_sim)
ALT_DATA_ROOTS = [
    ROOT / "data" / "mushroom" / "Freebase13",
    ROOT.parent / "data" / "mushroom" / "Freebase13",
]


def _resolve_freebase13_dir(path: Path) -> Path:
    path = path.resolve()
    if path.is_dir() and _find_split_files(path):
        return path
    for alt in ALT_DATA_ROOTS:
        if alt.is_dir() and _find_split_files(alt):
            return alt
    return path


def _find_split_files(directory: Path) -> dict[str, Path]:
    """Locate train/valid/test decoded files (with or without .clean suffix)."""
    names = {
        "train": ["train_decoded_mushroom.txt", "train_decoded_mushroom.txt.clean"],
        "valid": ["valid_decoded_mushroom.txt", "valid_decoded_mushroom.txt.clean"],
        "test": ["test_decoded_mushroom.txt", "test_decoded_mushroom.txt.clean"],
    }
    found: dict[str, Path] = {}
    for key, candidates in names.items():
        for name in candidates:
            p = directory / name
            if p.is_file():
                found[key] = p
                break
        if key not in found:
            for p in sorted(directory.glob(f"*{key}*mushroom*")):
                if p.is_file():
                    found[key] = p
                    break
    return found


def _read_positive(path: Path) -> list[tuple[str, str, str]]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            h, t, r = parts[0], parts[1], parts[2]
            rows.append((h, r, t))
    return rows


def _read_test(path: Path) -> list[tuple[str, str, str, int]]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            h, t, r, lab = parts[0], parts[1], parts[2], parts[3]
            label = 1 if lab in ("True", "1", "true") else 0
            rows.append((h, r, t, label))
    return rows


def build_pairs_paper(
    freebase13_dir: Path,
    max_groups: int | None = None,
) -> list[tuple[str, str, str, int]]:
    """Test set only: one positive + one negative tail per (head, relation) — paper VI-B style."""
    freebase13_dir = _resolve_freebase13_dir(freebase13_dir)
    files = _find_split_files(freebase13_dir)
    if "test" not in files:
        raise SystemExit(f"No test file under {freebase13_dir}")

    pos: dict[tuple[str, str], str] = {}
    neg: dict[tuple[str, str], str] = {}
    for h, r, t, label in _read_test(files["test"]):
        key = (h, r)
        if label == 1 and key not in pos:
            pos[key] = t
        elif label == 0 and key not in neg:
            neg[key] = t

    keys = sorted(k for k in pos if k in neg)
    if max_groups:
        keys = keys[:max_groups]

    out: list[tuple[str, str, str, int]] = []
    for key in keys:
        h, r = key
        out.append((h, r, pos[key], 1))
        out.append((h, r, neg[key], 0))
    return out


def build_pairs(
    freebase13_dir: Path,
    max_groups: int | None = None,
) -> list[tuple[str, str, str, int]]:
    freebase13_dir = _resolve_freebase13_dir(freebase13_dir)
    files = _find_split_files(freebase13_dir)
    if not files:
        hint = (
            f"No train/valid/test files under {freebase13_dir}.\n"
            "Expected e.g. train_decoded_mushroom.txt or train_decoded_mushroom.txt.clean\n"
            f"Also tried: {', '.join(str(p) for p in ALT_DATA_ROOTS)}"
        )
        raise SystemExit(hint)

    train = _read_positive(files.get("train", Path()))
    valid = _read_positive(files.get("valid", Path()))
    test = _read_test(files.get("test", Path()))

    true_tails: dict[tuple[str, str], set[str]] = defaultdict(set)
    for h, r, t in train + valid:
        true_tails[(h, r)].add(t)

    group_rows: dict[tuple[str, str], list[tuple[str, str, str, int]]] = defaultdict(list)
    seen: dict[tuple[str, str], set[tuple[str, int]]] = defaultdict(set)

    def add(h: str, r: str, t: str, label: int):
        key = (h, r)
        sig = (t, label)
        if sig in seen[key]:
            return
        seen[key].add(sig)
        group_rows[key].append((h, r, t, label))

    for h, r, t in train + valid:
        add(h, r, t, 1)

    for h, r, t, label in test:
        add(h, r, t, label)

    # Prefer groups with both correct and incorrect (paper-style contrast)
    keys = sorted(group_rows.keys())
    rich = [k for k in keys if any(l == 1 for *_, l in group_rows[k]) and any(l == 0 for *_, l in group_rows[k])]
    poor = [k for k in keys if k not in rich]
    ordered = rich + poor
    if max_groups:
        ordered = ordered[:max_groups]

    out: list[tuple[str, str, str, int]] = []
    for k in ordered:
        out.extend(group_rows[k])
    return out


def main():
    ap = argparse.ArgumentParser(description="mushroom Freebase13 → fb13_pairs.tsv")
    ap.add_argument(
        "--freebase13-dir",
        type=Path,
        required=True,
        help="Path to extracted Freebase13/ (contains train_decoded_mushroom.txt etc.)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-groups", type=int, default=None, help="e.g. 100 for paper-scale experiment")
    ap.add_argument(
        "--mode",
        choices=("full", "paper"),
        default="paper",
        help="paper=test-only 1 pos+1 neg per (h,r); full=train+valid+test",
    )
    args = ap.parse_args()

    fb_dir = _resolve_freebase13_dir(args.freebase13_dir)
    print(f"Using Freebase13 dir: {fb_dir}")
    print(f"Files: {_find_split_files(fb_dir)}")

    if args.mode == "paper":
        rows = build_pairs_paper(fb_dir, max_groups=args.max_groups)
    else:
        rows = build_pairs(fb_dir, max_groups=args.max_groups)
    if not rows:
        raise SystemExit(f"No rows parsed from {fb_dir}. Check file format.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        for h, r, t, lab in rows:
            w.writerow([h, r, t, lab])

    n_groups = len({(h, r) for h, r, _, _ in rows})
    print(f"Wrote {len(rows)} triples, {n_groups} (head,relation) groups → {args.out}")


if __name__ == "__main__":
    main()
