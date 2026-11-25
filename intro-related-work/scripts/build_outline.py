#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从事实底稿与文献清单生成引言 4 段式骨架。

用法:
    python3 build_outline.py --facts facts.json --refs refs.json --out work/outline.json
"""
import argparse
import json
import os
import sys


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", required=True)
    ap.add_argument("--refs", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    facts = load(args.facts, {}) or {}
    refs = (load(args.refs, {}) or {}).get("refs") or (load(args.refs, {}) or [])
    if isinstance(refs, dict):
        refs = refs.get("items", [])

    groups = {}
    for r in refs:
        g = r.get("group") or "general"
        groups.setdefault(g, []).append(r.get("key") or r.get("id") or r.get("title", "")[:30])

    outline = {
        "background": {
            "points": facts.get("background") or [
                "领域脉络：该问题为什么现在值得做",
                "具体问题：现有方法在什么条件下失效",
                "技术约束：数据/成本/部署限制",
            ],
            "must_cite": [k for k in sum(groups.values(), [])][:3],
        },
        "related_work": [
            {"group": g, "refs": keys, "limitation": "该组共同限制：待写"}
            for g, keys in groups.items()
        ],
        "gap": {"text": "由上述各组共同限制推出：待写", "refs": [k for g in groups.values() for k in g][:2]},
        "contributions": [
            {"text": c.get("text", ""), "evidence": c.get("evidence", "")}
            for c in (facts.get("contributions") or [])
        ],
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "groups": len(groups), "refs": len(refs),
                      "contributions": len(outline["contributions"])}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
