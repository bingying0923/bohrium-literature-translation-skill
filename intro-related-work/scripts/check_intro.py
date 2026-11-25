#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验引言：引用覆盖 / 空转句 / 分组维度 / 空白推导 / 贡献证据 / 引用有效性。

用法:
    python3 check_intro.py --intro work/intro.json --refs refs.json --facts facts.json --out work/check.json
"""
import argparse
import json
import os
import re
import sys

CITE_RE = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]|\([A-Z][A-Za-z\-']+(?:\s+et\s+al\.?)?,?\s*(?:19|20)\d{2}\)")
EMPTY_PHRASES = [
    r"widely (?:studied|investigated|used)", r"received (?:much|increasing) attention",
    r"has attracted (?:much|great) attention", r"具有重要意义", r"受到广泛关注",
    r"随着.{0,10}的发展", r"plays? an important role", r"众所周知",
]
EVIDENCE_RE = re.compile(r"(?:Fig(?:ure)?\.?|Table|Eq\.?)\s*\d+|[\d.]+\s*(?:%|µg/L|mg/L|min|h)", re.I)


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--intro", required=True)
    ap.add_argument("--refs", required=True)
    ap.add_argument("--facts", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    intro = load(args.intro, {}) or {}
    refs = load(args.refs, {}) or {}
    if isinstance(refs, list):
        ref_items = refs
    else:
        ref_items = refs.get("refs") or refs.get("items") or []
    valid_keys = {str(r.get("key") or r.get("id") or "") for r in ref_items if isinstance(r, dict)}

    paras = intro.get("paragraphs") or []
    issues = {"coverage": [], "empty_phrases": [], "grouping": [], "gap_support": [],
              "contributions": [], "refs_valid": []}

    total, cited = 0, 0
    used_keys = set()
    for p in paras:
        role = p.get("role", "")
        text = p.get("text", "")
        if role in ("background", "related", "gap"):
            total += 1
            found = CITE_RE.findall(text) + list(p.get("citations") or [])
            if found or "[author-claim]" in text:
                cited += 1
            else:
                issues["coverage"].append({"where": p.get("id"), "issue": "无引用且未标注作者判断",
                                           "text": text[:80]})
        for pat in EMPTY_PHRASES:
            if re.search(pat, text, re.I):
                issues["empty_phrases"].append({"where": p.get("id"), "pattern": pat, "text": text[:80]})
        for k in (p.get("citations") or []):
            k = str(k)
            used_keys.add(k)
            if valid_keys and k not in valid_keys:
                issues["refs_valid"].append({"where": p.get("id"), "issue": "引用 key 不在文献清单", "key": k})

    rw = (intro.get("outline") or {}).get("related_work") or []
    if len(rw) < 2:
        issues["grouping"].append({"issue": "相关工作少于 2 组，未形成维度比较"})
    for g in rw:
        if len(g.get("refs") or []) < 2:
            issues["grouping"].append({"group": g.get("group"), "issue": "该组引用少于 2 篇"})

    gap = (intro.get("outline") or {}).get("gap") or {}
    if not (gap.get("refs") or []):
        issues["gap_support"].append({"issue": "研究空白未引用被限制文献"})

    contribs = (intro.get("outline") or {}).get("contributions") or []
    if not contribs:
        issues["contributions"].append({"issue": "未给出贡献条目"})
    for c in contribs:
        if not c.get("evidence") or not EVIDENCE_RE.search(str(c.get("evidence"))):
            issues["contributions"].append({"contribution": c.get("text", "")[:60],
                                            "issue": "贡献缺少可核对的证据（Fig./Table/数值）"})

    uncited = sorted(valid_keys - used_keys - {""})
    checks = {
        "coverage": {"ok": not issues["coverage"], "issues": issues["coverage"],
                      "rate": round(cited / total, 2) if total else 1.0},
        "empty_phrases": {"ok": not issues["empty_phrases"], "issues": issues["empty_phrases"]},
        "grouping": {"ok": not issues["grouping"], "issues": issues["grouping"]},
        "gap_support": {"ok": not issues["gap_support"], "issues": issues["gap_support"]},
        "contributions": {"ok": not issues["contributions"], "issues": issues["contributions"]},
        "refs_valid": {"ok": not issues["refs_valid"], "issues": issues["refs_valid"], "uncited": uncited},
    }
    blocking = sum(len(v["issues"]) for k, v in checks.items() if k != "refs_valid")
    out = {"checks": checks, "blocking": blocking, "ok": blocking == 0}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "blocking": blocking,
                      "coverage": checks["coverage"]["rate"],
                      "uncited": len(uncited)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
