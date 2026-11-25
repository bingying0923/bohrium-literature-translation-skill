#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从分段结果里抽候选术语, 合并已有术语表, 输出可锁定的 glossary.csv。

用法:
    python3 build_glossary.py --segments work/segments.json --out work/glossary.csv \
        [--existing my_glossary.csv] [--min-count 2]

glossary.csv 列: term,translation,locked,count,first_segment,first_page,context,note
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, OrderedDict

STOP = set("""a an the of in on at to for from by with without and or but if then than that this these those
is are was were be been being as it its their our we they he she his her not no may can could should would
also such more most less least between among during after before under over into within via using used use
here there which who whom whose what when where how all any both each few many some own same so only very
s t d ll m re ve y""".split())

ABBR_RE = re.compile(r"\b(?:[A-Z]{2,}[A-Za-z0-9-]*)\b")
CAPS_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]{1,}|[A-Z]{2,})(?:[-\s](?:[A-Z][a-z]{1,}|[A-Z]{2,}|\d+))*\b")
HYPHEN_RE = re.compile(r"\b[a-zA-Z]+(?:-[a-zA-Z]+){1,3}\b")
GREEK_RE = re.compile(r"\b(?:alpha|beta|gamma|delta|epsilon|theta|lambda|sigma|mu|tau|phi|omega)-?[a-zA-Z]*\b", re.I)


def norm_term(t):
    return re.sub(r"\s+", " ", t.strip())


def candidates(text):
    out = []
    for m in CAPS_PHRASE_RE.finditer(text):
        w = norm_term(m.group(0))
        if len(w) < 3:
            continue
        words = w.split()
        if all(x.lower() in STOP for x in words):
            continue
        if len(words) == 1 and w.islower():
            continue
        out.append(("phrase" if len(words) > 1 else "capital", w))
    for m in ABBR_RE.finditer(text):
        out.append(("abbr", m.group(0)))
    for m in HYPHEN_RE.finditer(text):
        out.append(("compound", m.group(0)))
    for m in GREEK_RE.finditer(text):
        out.append(("greek", m.group(0)))
    return out


def load_existing(path):
    locked, allrows = {}, {}
    if not path or not os.path.exists(path):
        return locked, allrows
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            t = norm_term(row.get("term", ""))
            if not t:
                continue
            allrows[t.lower()] = row
            if str(row.get("locked", "")).strip().lower() in ("1", "true", "yes", "y"):
                locked[t.lower()] = row
    return locked, allrows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--existing", default=None)
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--max-terms", type=int, default=300)
    args = ap.parse_args()

    with open(args.segments, "r", encoding="utf-8") as f:
        data = json.load(f)
    segs = data.get("segments", [])

    counts, first, contexts = Counter(), {}, {}
    for s in segs:
        if s.get("section") == "References":
            continue
        for kind, term in candidates(s.get("source", "")):
            key = term.lower()
            counts[key] += 1
            first.setdefault(key, (s["id"], s.get("page", 0), kind))
            contexts.setdefault(key, s.get("source", "")[:160])

    locked, existing = load_existing(args.existing)
    rows = OrderedDict()
    for key, cnt in counts.most_common():
        if cnt < args.min_count and key not in existing:
            continue
        sid, page, kind = first[key]
        row = existing.get(key, {})
        rows[key] = {
            "term": row.get("term") or key,
            "translation": row.get("translation", ""),
            "locked": "true" if key in locked else (row.get("locked", "false") or "false"),
            "count": cnt,
            "first_segment": sid,
            "first_page": page,
            "context": row.get("context") or contexts.get(key, "").replace("\n", " ")[:160],
            "note": row.get("note", ""),
        }
        if len(rows) >= args.max_terms:
            break

    # 还原原始大小写
    raw_by_key = {}
    for s in segs:
        for kind, term in candidates(s.get("source", "")):
            raw_by_key.setdefault(term.lower(), term)
    for key, row in rows.items():
        row["term"] = (existing.get(key, {}).get("term") or raw_by_key.get(key, key))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["term", "translation", "locked", "count",
                                          "first_segment", "first_page", "context", "note"])
        w.writeheader()
        for row in rows.values():
            w.writerow(row)
    print(json.dumps({"status": "ok", "out": args.out, "terms": len(rows),
                      "locked": sum(1 for r in rows.values() if r["locked"] == "true")},
                     ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
