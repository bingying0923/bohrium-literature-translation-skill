#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为每条断言在原文中找最小充分证据片段并打分。

用法:
    python3 bind_evidence.py --claims work/claims.json --paper paper.md --out work/bound.json
"""
import argparse
import json
import os
import re
import sys

PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
STOP = set("""a an the of in on at to for from by with without and or but if then than that this these those
is are was were be been being as it its their our we they he she his her not no may can could should would
also such more most less least between among during after before under over into within via using used use
here there which who whom whose what when where how all any both each few many some own same so only very""".split())


def tokens(text):
    ws = re.findall(r"[A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff\-]*", text.lower())
    return [w for w in ws if w not in STOP and len(w) > 1]


def read(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return open(path, "r", encoding=enc).read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def build_pool(raw):
    pool, page, para = [], 1, 0
    buf = []
    def flush():
        nonlocal buf
        if not buf:
            return
        text = " ".join(buf).strip()
        buf = []
        for s in SENT_SPLIT.split(text):
            s = s.strip()
            if len(s) >= 12:
                pool.append({"anchor": "p%03d" % para, "page": page, "text": s})
    for ln in raw.split("\n"):
        m = PAGE_RE.match(ln.strip())
        if m:
            flush(); page = int(m.group(1)); continue
        if not ln.strip():
            flush(); para += 1; continue
        buf.append(ln.strip())
    flush()
    return pool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", required=True)
    ap.add_argument("--paper", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.35)
    args = ap.parse_args()

    with open(args.claims, "r", encoding="utf-8") as f:
        claims = json.load(f).get("claims", [])
    pool = build_pool(read(args.paper))

    bound = []
    for c in claims:
        ct = set(tokens(c["text"]))
        best, best_score = None, 0.0
        for s in pool:
            st = set(tokens(s["text"]))
            if not ct or not st:
                continue
            inter = len(ct & st)
            score = inter / max(1, min(len(ct), len(st)))
            if score > best_score or (score == best_score and best and len(s["text"]) < len(best["text"])):
                best, best_score = s, score
        nums = c.get("numbers") or []
        num_ok = all(n in (best["text"] if best else "") for n in nums) if nums else True
        kind = "direct" if best_score >= 0.6 else ("inferred" if best_score >= args.threshold else "weak")
        bound.append({
            "id": c["id"],
            "text": c["text"],
            "evidence": {
                "anchor": best["anchor"] if best else "",
                "page": best["page"] if best else None,
                "text": best["text"] if best else "",
                "score": round(best_score, 3),
                "kind": kind,
                "numbers_preserved": num_ok,
            },
        })

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"bound": bound}, f, ensure_ascii=False, indent=1)
    weak = sum(1 for b in bound if b["evidence"]["kind"] == "weak")
    print(json.dumps({"status": "ok", "bound": len(bound), "weak": weak,
                      "avg_score": round(sum(b["evidence"]["score"] for b in bound) / max(1, len(bound)), 3)},
                     ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
