#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nanopublication 质量检查：过宽断言 / 证据不足 / 来源缺失 / 重复 / 主体混淆。

用法:
    python3 validate_nanopub.py --claims work/claims.json --bound work/bound.json \
        --meta meta.json --out work/validation.json
"""
import argparse
import json
import os
import re
import sys

STOP = set("the a an of in on at to for from by with and or but if then than".split())


def norm(text):
    return re.sub(r"\W+", " ", text.lower()).strip()


def jaccard(a, b):
    A, B = set(norm(a).split()), set(norm(b).split())
    return len(A & B) / max(1, len(A | B))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", required=True)
    ap.add_argument("--bound", required=True)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.claims, "r", encoding="utf-8") as f:
        claims = {c["id"]: c for c in json.load(f).get("claims", [])}
    with open(args.bound, "r", encoding="utf-8") as f:
        bound = {b["id"]: b for b in json.load(f).get("bound", [])}
    meta = {}
    if args.meta and os.path.exists(args.meta):
        with open(args.meta, "r", encoding="utf-8-sig") as f:
            meta = json.load(f)

    issues = []
    seen = []
    for cid, c in claims.items():
        b = bound.get(cid, {}).get("evidence", {})

        if c.get("quantifiers") and not c.get("conditions"):
            issues.append({"claim_id": cid, "issue": "overbroad",
                           "why": "断言含绝对数量词 %s 但没有条件限定" % c["quantifiers"],
                           "suggested_action": "补条件（in/under/when）或把绝对词改为限定表述"})

        if not b or b.get("score", 0) < 0.35:
            issues.append({"claim_id": cid, "issue": "weak_evidence",
                           "why": "最佳证据匹配分数 %.2f（<0.35）" % (b.get("score", 0) or 0),
                           "suggested_action": "回到原文找直接支撑句；若为推论请标注 inferred 并降级"})

        if b and c.get("numbers") and not b.get("numbers_preserved", True):
            issues.append({"claim_id": cid, "issue": "evidence_number_mismatch",
                           "why": "断言中的数值未出现在证据句中",
                           "suggested_action": "换更贴合的原文句，或核对数值来源"})

        for d in seen:
            if jaccard(d["text"], c["text"]) > 0.9:
                issues.append({"claim_id": cid, "issue": "duplicate",
                               "why": "与 %s 高度重复（Jaccard>0.9）" % d["id"],
                               "suggested_action": "合并为一条断言"})
                break
        seen.append({"id": cid, "text": c["text"]})

        ev_text = (b.get("text") or "").lower()
        head = norm(c["text"]).split(" ")[0] if c["text"] else ""
        if ev_text and head and head not in ev_text and head not in STOP:
            issues.append({"claim_id": cid, "issue": "subject_check",
                           "why": "断言起始词「%s」未出现在证据句中，需人工确认主体一致" % head,
                           "suggested_action": "核对主语是否被指代替换（this/these）"})

    for field in ("title", "year", "authors", "source_file"):
        if not meta.get(field):
            issues.append({"claim_id": "", "issue": "missing_source",
                           "why": "来源元数据缺 %s" % field,
                           "suggested_action": "补论文元数据后再导出"})

    blocking = len([i for i in issues if i["issue"] in ("weak_evidence", "missing_source", "evidence_number_mismatch")])
    out = {"issues": issues, "blocking": blocking,
           "ok": blocking == 0,
           "counts": {k: len([i for i in issues if i["issue"] == k])
                      for k in ("overbroad", "weak_evidence", "duplicate", "missing_source",
                                "evidence_number_mismatch", "subject_check")}}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "blocking": blocking, "counts": out["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
