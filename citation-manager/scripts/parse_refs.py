#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析正文引用标记与文末参考文献列表。

用法:
    python3 parse_refs.py --input manuscript.md --out work/refs.json

输出:
    {"citations":[{"anchor","raw","numbers","style"}],
     "entries":[{"index","raw","authors","year","title","venue","doi","key"}],
     "list_style":"numeric|author-year|unknown"}
"""
import argparse
import json
import os
import re
import sys

NUM_CITE = re.compile(r"\[\s*(\d+(?:\s*[-–,，]\s*\d+)*)\s*\]")
AUTHOR_CITE = re.compile(r"\(([A-Z][A-Za-z\-']+(?:\s+(?:et\s+al\.?|and\s+[A-Z][A-Za-z\-']+))?),\s*((?:19|20)\d{2})[a-z]?\)")
REF_START = re.compile(r"^\s*\[?(\d{1,3})[\].)]\s+")
YEAR = re.compile(r"\b(19|20)\d{2}\b")
DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
TITLE_Q = re.compile(r"[“\"']([^”\"']{8,200})[”\"']")


def expand(nums_text):
    out = []
    for part in re.split(r"[,，]", nums_text):
        part = part.strip()
        m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b and b - a <= 100:
                out.extend(range(a, b + 1))
                continue
        if part.isdigit():
            out.append(int(part))
    return out


def read(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return open(path, "r", encoding=enc).read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def split_body_refs(text):
    lines = text.split("\n")
    idx = None
    for i, ln in enumerate(lines):
        if re.match(r"^#{0,6}\s*(references|bibliography|参考文献)\s*$", ln.strip(), re.I):
            idx = i
            break
    if idx is None:
        return text, ""
    return "\n".join(lines[:idx]), "\n".join(lines[idx + 1:])


def parse_entries(block):
    entries, cur = [], None
    for ln in block.split("\n"):
        m = REF_START.match(ln)
        if m:
            if cur:
                entries.append(cur)
            cur = {"index": int(m.group(1)), "raw": ln[m.end():].strip()}
        elif ln.strip() and cur:
            cur["raw"] += " " + ln.strip()
    if cur:
        entries.append(cur)

    for e in entries:
        raw = e["raw"]
        ym = YEAR.search(raw)
        e["year"] = ym.group(0) if ym else ""
        dm = DOI.search(raw)
        e["doi"] = dm.group(0) if dm else ""
        tm = TITLE_Q.search(raw)
        e["title"] = tm.group(1).strip() if tm else ""
        if not e["title"]:
            parts = [p.strip() for p in re.split(r"\.\s+", raw) if p.strip()]
            e["title"] = parts[1] if len(parts) > 1 else (parts[0] if parts else "")
        authors = re.split(r"\.\s+", raw)[0]
        e["authors"] = authors[:120]
        e["venue"] = raw[raw.find(e["title"]) + len(e["title"]):][:120].strip(" .,;") if e["title"] else ""
        e["key"] = (e["doi"].lower() or re.sub(r"\W+", "", (e["title"] or "").lower())[:60])
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = read(args.input)
    body, refblock = split_body_refs(text)

    citations = []
    para = 0
    for ln in body.split("\n"):
        if not ln.strip():
            para += 1
            continue
        for m in NUM_CITE.finditer(ln):
            citations.append({"anchor": "p%03d" % (para + 1), "raw": m.group(0),
                              "numbers": expand(m.group(1)), "style": "numeric"})
        for m in AUTHOR_CITE.finditer(ln):
            citations.append({"anchor": "p%03d" % (para + 1), "raw": m.group(0),
                              "numbers": [], "style": "author-year",
                              "author": m.group(1), "year": m.group(2)})

    entries = parse_entries(refblock) if refblock.strip() else []
    style = "numeric" if entries and all(str(e["index"]).isdigit() for e in entries) else (
        "author-year" if not entries and any(c["style"] == "author-year" for c in citations) else "unknown")

    out = {"body": body, "reference_block": refblock, "citations": citations,
           "entries": entries, "list_style": style,
           "stats": {"citations": len(citations), "entries": len(entries)}}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "citations": len(citations), "entries": len(entries),
                      "style": style}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())

