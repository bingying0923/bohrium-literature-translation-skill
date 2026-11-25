#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核查正文引用与文末列表的一致性、编号顺序、重复条目与缺失字段。

用法:
    python3 audit_citations.py --refs work/refs.json --out work/audit.json
"""
import argparse
import json
import os
import sys
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.refs, "r", encoding="utf-8") as f:
        data = json.load(f)
    cites = data.get("citations", [])
    entries = data.get("entries", [])
    idx = {e["index"]: e for e in entries}

    cited = []
    for c in cites:
        cited.extend(c.get("numbers") or [])
    cited_set = set(cited)

    missing = sorted({n for n in cited_set if n not in idx})          # 正文引了但列表没有
    uncited = sorted({e["index"] for e in entries} - cited_set)        # 列表有但正文没引
    gaps = []
    if entries:
        nums = sorted(idx)
        for a, b in zip(nums, nums[1:]):
            if b != a + 1:
                gaps.extend(range(a + 1, b))

    first_order, seen = [], set()
    for c in cites:
        for n in (c.get("numbers") or []):
            if n not in seen:
                seen.add(n)
                first_order.append(n)
    order_ok = first_order == sorted(first_order)

    dups = []
    by_key = {}
    for e in entries:
        k = e.get("key")
        if k:
            by_key.setdefault(k, []).append(e["index"])
    for k, ids in by_key.items():
        if len(ids) > 1:
            dups.append({"key": k, "indices": ids})

    incomplete = [{"index": e["index"], "missing": [f for f in ("authors", "year", "title") if not e.get(f)]}
                  for e in entries if not all(e.get(f) for f in ("authors", "year", "title"))]

    numeric_in_author_year = [c["raw"] for c in cites if data.get("list_style") == "author-year" and c["style"] == "numeric"]
    author_year_in_numeric = [c["raw"] for c in cites if data.get("list_style") == "numeric" and c["style"] == "author-year"]

    issues = {
        "missing_references": missing,
        "uncited_references": uncited,
        "numbering_gaps": gaps,
        "order_of_appearance_ok": order_ok,
        "first_appearance_order": first_order,
        "duplicates": dups,
        "incomplete_entries": incomplete,
        "style_mixed": {"numeric_in_author_year": numeric_in_author_year,
                        "author_year_in_numeric": author_year_in_numeric},
    }
    blocking = len(missing) + len(uncited) + len(gaps) + len(dups) + len(incomplete)
    audit = {"issues": issues, "blocking": blocking, "ok": blocking == 0,
             "counts": {"cited": len(cited_set), "entries": len(entries),
                        "duplicates": len(dups), "missing": len(missing), "uncited": len(uncited)}}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "blocking": blocking, "missing": missing,
                      "uncited": uncited, "gaps": gaps, "dups": len(dups)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
