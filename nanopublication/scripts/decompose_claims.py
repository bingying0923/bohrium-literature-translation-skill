#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把论文段落拆成原子断言。

用法:
    python3 decompose_claims.py --input paper.md --out work/claims.json
"""
import argparse
import json
import os
import re
import sys

PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
CLAUSE_SPLIT = re.compile(r"\s*(?:;|；|,\s+(?:and|but|whereas|while|although)\s+)\s*", re.I)
HEDGES = ["may", "might", "could", "suggest", "indicates", "appears", "likely", "possibly", "partly", "in part"]
QUANTS = ["all", "always", "never", "every", "each", "none", "所有", "总是", "从未"]
COND = re.compile(r"\b(?:in|under|when|at|for|after|before|with)\b[^,.;]{2,40}", re.I)
NUM = re.compile(r"\d+(?:[.,]\d+)*")
CMP = re.compile(r"\b(higher|lower|greater|less|increase[sd]?|decrease[sd]?|improve[sd]?|reduce[sd]?)\b", re.I)
METHOD = re.compile(r"\b(we|our)\s+(?:used|developed|collected|measured|fitted|applied|built)\b", re.I)
LIMIT = re.compile(r"\b(limitation|caveat|not (?:tested|validated)|only|future work)\b", re.I)


def read(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return open(path, "r", encoding=enc).read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def classify(text):
    if LIMIT.search(text):
        return "limitation"
    if METHOD.search(text):
        return "method"
    if NUM.search(text) or CMP.search(text):
        return "finding"
    return "claim"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    raw = read(args.input)
    page, para, claims = 1, 0, []
    buf = []
    cid = 0

    def flush_para():
        nonlocal buf, cid
        if not buf:
            return
        text = " ".join(buf).strip()
        buf = []
        if not text:
            return
        for sent in SENT_SPLIT.split(text):
            sent = sent.strip()
            if len(sent) < 8:
                continue
            for clause in CLAUSE_SPLIT.split(sent):
                clause = clause.strip(" .,;")
                if len(clause) < 12:
                    continue
                cid += 1
                claims.append({
                    "id": "c%03d" % cid,
                    "anchor": "p%03d" % para,
                    "page": page,
                    "text": clause,
                    "type": classify(clause),
                    "hedges": [h for h in HEDGES if re.search(r"\b" + h + r"\b", clause, re.I)],
                    "quantifiers": [q for q in QUANTS if re.search(r"\b" + q + r"\b", clause, re.I)],
                    "conditions": [m.group(0) for m in COND.finditer(clause)][:3],
                    "numbers": NUM.findall(clause),
                })

    for ln in raw.split("\n"):
        m = PAGE_RE.match(ln.strip())
        if m:
            flush_para()
            page = int(m.group(1))
            continue
        if not ln.strip():
            flush_para()
            para += 1
            continue
        buf.append(ln.strip())
    flush_para()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"claims": claims}, f, ensure_ascii=False, indent=1)
    types = {}
    for c in claims:
        types[c["type"]] = types.get(c["type"], 0) + 1
    print(json.dumps({"status": "ok", "claims": len(claims), "types": types}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
