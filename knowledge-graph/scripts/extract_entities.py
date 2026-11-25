#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从论文文本抽取科研实体（方法/材料/指标/任务/结论），带原文锚点。

用法:
    python3 extract_entities.py --input paper.md --out work/entities.json
"""
import argparse
import json
import os
import re
import sys

PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

DICT = {
    "method": [r"ICP-MS", r"HPLC", r"GC-MS", r"PCR", r"ELISA", r"fluorescence",
               r"(?:[a-z\-]+ ){0,2}(?:sensor|assay|method|model|curve|chromatograph\w*|spectromet\w*|spectrophotomet\w*)"],
    "material": [r"(?:[a-z\-]+ ){0,2}(?:membrane|nanoparticle|electrode|hydrogel|aptamer|antibody|quantum dot|graphene)"],
    "metric": [r"limit of detection", r"\bLOD\b", r"recovery", r"\bRSD\b", r"sensitivity",
               r"selectivity", r"AUC", r"accuracy", r"precision", r"slope"],
    "task": [r"(?:detection|quantification|screening|monitoring|classification|prediction)(?: of [a-z ]{3,25})?"],
    "finding": [r"(?:ranged from|was lower than|was higher than|increased|decreased)[^.]{3,80}"],
}
CITATION = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")


def read(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return open(path, "r", encoding=enc).read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    raw = read(args.input)
    sentences, page, para = [], 1, 0
    buf = []
    def flush():
        nonlocal buf
        if not buf:
            return
        text = " ".join(buf).strip()
        buf = []
        for s in SENT_SPLIT.split(text):
            s = s.strip()
            if len(s) >= 10 and not CITATION.fullmatch(s):
                sentences.append({"anchor": "p%03d" % para, "page": page, "text": s})
    for ln in raw.split("\n"):
        m = PAGE_RE.match(ln.strip())
        if m:
            flush(); page = int(m.group(1)); continue
        if not ln.strip():
            flush(); para += 1; continue
        buf.append(ln.strip())
    flush()

    ents, seen = [], {}
    for s in sentences:
        for etype, pats in DICT.items():
            for pat in pats:
                for m in re.finditer(pat, s["text"], re.I):
                    surface = m.group(0).strip()
                    if len(surface) < 2:
                        continue
                    key = (etype, surface.lower())
                    if key in seen:
                        continue
                    seen[key] = True
                    ents.append({
                        "id": "n%03d" % (len(ents) + 1),
                        "type": etype,
                        "surface": surface,
                        "anchor": s["anchor"],
                        "page": s["page"],
                        "sentence": s["text"][:240],
                    })
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"entities": ents}, f, ensure_ascii=False, indent=1)
    by_type = {}
    for e in ents:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    print(json.dumps({"status": "ok", "entities": len(ents), "by_type": by_type}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())

