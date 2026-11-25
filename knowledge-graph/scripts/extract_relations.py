#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽取有证据支撑的实体关系（uses / measures / outperforms / reports / limitation_of）。

做法：在同时出现 ≥2 个已知实体的句子里，用线索词判定关系类型与方向。

用法:
    python3 extract_relations.py --entities work/entities.json --input paper.md --out work/relations.json
"""
import argparse
import json
import os
import re
import sys

PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

CUES = [
    ("uses", re.compile(r"\b(?:uses?|used|employs?|based on|relies on|relied on)\b", re.I)),
    ("measures", re.compile(r"\b(?:measures?|measured|quantif(?:y|ies|ied)|detects?|detected)\b", re.I)),
    ("outperforms", re.compile(r"\b(?:lower|higher|better|smaller|greater)\s+than\b", re.I)),
    ("reports", re.compile(r"\b(?:reported|achieved|ranged from|showed|yielded)\b", re.I)),
]
LIMIT_RE = re.compile(r"\b(?:only|not (?:yet )?(?:tested|validated)|limited to)\b", re.I)


def read(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return open(path, "r", encoding=enc).read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def sentences(raw):
    out, page, para, buf = [], 1, 0, []
    def flush():
        nonlocal buf
        if not buf:
            return
        text = " ".join(buf).strip()
        buf = []
        for s in SENT_SPLIT.split(text):
            if len(s.strip()) >= 10:
                out.append({"anchor": "p%03d" % para, "page": page, "text": s.strip()})
    for ln in raw.split("\n"):
        m = PAGE_RE.match(ln.strip())
        if m:
            flush(); page = int(m.group(1)); continue
        if not ln.strip():
            flush(); para += 1; continue
        buf.append(ln.strip())
    flush()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entities", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.entities, "r", encoding="utf-8") as f:
        ents = json.load(f).get("entities", [])

    rels, rid, seen = [], 0, set()
    for s in sentences(read(args.input)):
        low = s["text"].lower()
        present = [e for e in ents if e["surface"].lower() in low]
        if len(present) < 2:
            continue
        present.sort(key=lambda e: low.find(e["surface"].lower()))
        for rtype, cue in CUES:
            if not cue.search(s["text"]):
                continue
            a, b = present[0], present[-1]
            key = (a["id"], b["id"], rtype)
            if a["id"] == b["id"] or key in seen:
                continue
            seen.add(key)
            rid += 1
            rels.append({"id": "e%03d" % rid, "source": a["id"], "target": b["id"], "type": rtype,
                         "direction": "forward", "evidence": s["text"][:240],
                         "anchor": s["anchor"], "strength": "direct" if len(s["text"]) < 180 else "weak"})
        if LIMIT_RE.search(s["text"]):
            rid += 1
            rels.append({"id": "e%03d" % rid, "source": present[-1]["id"], "target": present[0]["id"],
                         "type": "limitation_of", "direction": "forward",
                         "evidence": s["text"][:240], "anchor": s["anchor"], "strength": "direct"})

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"relations": rels}, f, ensure_ascii=False, indent=1)
    by_type = {}
    for r in rels:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    print(json.dumps({"status": "ok", "relations": len(rels), "by_type": by_type}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
