#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽取术语候选并合并既有术语表，输出可锁定的 terms.csv。

用法:
    python3 build_terms.py --units work/units.json --out work/terms.csv [--existing old.csv]

terms.csv 列: term,preferred,locked,count,first_unit,note
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
we i our""".split())

ABBR_RE = re.compile(r"\b[A-Z]{2,}[A-Za-z0-9\-]*\b")
PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]{1,}|[A-Z]{2,})(?:[-\s](?:[A-Z][a-z]{1,}|[A-Z]{2,}|\d+))*\b")
HYPHEN_RE = re.compile(r"\b[a-zA-Z]+(?:-[a-zA-Z]+){1,3}\b")


def norm(s):
    return re.sub(r"\s+", " ", s.strip())


def load_existing(path):
    locked, rows = {}, {}
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                t = norm(r.get("term", ""))
                if not t:
                    continue
                rows[t.lower()] = r
                if str(r.get("locked", "")).lower() in ("1", "true", "yes"):
                    locked[t.lower()] = r
    return locked, rows


def candidates(text):
    out = []
    for m in PHRASE_RE.finditer(text):
        w = norm(m.group(0))
        if len(w) < 3:
            continue
        words = w.split()
        if all(x.lower() in STOP for x in words):
            continue
        out.append(w)
    for m in ABBR_RE.finditer(text):
        out.append(m.group(0))
    for m in HYPHEN_RE.finditer(text):
        out.append(m.group(0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--existing", default=None)
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--max-terms", type=int, default=200)
    args = ap.parse_args()

    with open(args.units, "r", encoding="utf-8") as f:
        units = json.load(f).get("units", [])

    cnt, first, raw_case = Counter(), {}, {}
    for u in units:
        for t in candidates(u.get("original", "")):
            k = t.lower()
            cnt[k] += 1
            first.setdefault(k, u["id"])
            raw_case.setdefault(k, t)

    locked, existing = load_existing(args.existing)
    rows = OrderedDict()
    for k, c in cnt.most_common():
        if c < args.min_count and k not in existing:
            continue
        r = existing.get(k, {})
        rows[k] = {
            "term": r.get("term") or raw_case.get(k, k),
            "preferred": r.get("preferred", ""),
            "locked": "true" if k in locked else (r.get("locked", "false") or "false"),
            "count": c,
            "first_unit": first.get(k, ""),
            "note": r.get("note", ""),
        }
        if len(rows) >= args.max_terms:
            break

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["term", "preferred", "locked", "count", "first_unit", "note"])
        w.writeheader()
        for row in rows.values():
            w.writerow(row)
    print(json.dumps({"status": "ok", "out": args.out, "terms": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
