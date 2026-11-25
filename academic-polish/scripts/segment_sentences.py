#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把稿件切成段落/句子单元，并识别需要原样保留的保护块。

用法:
    python3 segment_sentences.py --input input.md --out work/units.json

输出 units.json:
    {"doc": {...}, "units": [{"id","paragraph","original",
                              "protected":{"numbers","units","citations","figures","hedges"}}]}
"""
import argparse
import json
import os
import re
import sys

NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
UNIT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(%|‰|mg|g|kg|µg|ng|mL|L|µL|mm|cm|m|km|nm|s|min|h|d|"
                     r"°C|℃|K|Pa|kPa|MPa|Hz|kHz|MHz|V|mV|mA|A|W|kW|J|kJ|kcal|mol|mM|µM|nM|M|"
                     r"rpm|Da|kDa|ppm|ppb)\b")
CITE_RE = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")
AUTHOR_CITE_RE = re.compile(r"\([A-Z][A-Za-z\-']+(?:\s+et\s+al\.?)?,?\s*(?:19|20)\d{2}[a-z]?\)")
FIG_RE = re.compile(r"(?:Fig(?:ure)?\.?|Table|Eq(?:uation)?\.?|Section|Supplementary)\s*\(?\d+[A-Za-z]?\)?")
HEDGE_WORDS = [
    "may", "might", "could", "would", "can", "suggest", "suggests", "suggested",
    "indicate", "indicates", "indicated", "appear", "appears", "appeared",
    "tend", "tends", "tended", "likely", "unlikely", "possibly", "probably",
    "potentially", "partly", "partially", "in part", "somewhat", "relatively",
    "approximately", "about", "around", "seem", "seems", "seemed", "assume",
    "assumed", "hypothesize", "hypothesized", "propose", "proposed",
]
NEG_RE = re.compile(r"\b(?:not|no|none|never|neither|nor|without|lack(?:s|ed)?|"
                    r"cannot|can't|isn't|aren't|wasn't|weren't|doesn't|don't|didn't|fail(?:s|ed)?\s+to)\b", re.I)

PROTECT_PATTERNS = [
    re.compile(r"\$[^$]{1,200}\$"),
    re.compile(r"\\begin\{[a-zA-Z*]+\}.*?\\end\{[a-zA-Z*]+\}", re.S),
    re.compile(r"\\[a-zA-Z]+\{[^{}]{0,120}\}"),
    re.compile(r"https?://\S+"),
    re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b"),
]


def protect_spans(text):
    spans = []
    for pat in PROTECT_PATTERNS:
        for m in pat.finditer(text):
            spans.append((m.start(), m.end()))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


ABBR = {"fig", "figs", "figure", "eq", "eqs", "equation", "ref", "refs", "al", "e.g", "i.e",
        "vs", "no", "vol", "pp", "approx", "cf", "resp", "sec", "tab", "suppl"}


def _word_before(text, idx):
    j = idx - 1
    while j >= 0 and (text[j].isalpha() or text[j] == "."):
        j -= 1
    return text[j + 1:idx].strip(".").lower()


def split_sentences(text):
    """在保护块之外按 . ! ? 断句。"""
    spans = protect_spans(text)
    cuts, start = [], 0
    i = 0
    n = len(text)
    while i < n:
        inside = any(s <= i < e for s, e in spans)
        ch = text[i]
        if not inside and ch in ".!?。！？":
            j = i + 1
            while j < n and text[j] in "\"'”’)）]":
                j += 1
            rest = text[j:]
            nxt = rest.lstrip()[:1]
            if _word_before(text, i) in ABBR or nxt.isdigit():
                i += 1
                continue
            if rest == "" or rest[:1].isspace():
                cuts.append((start, j))
                start = j
                i = j
                continue
        i += 1
    if start < n:
        cuts.append((start, n))
    out = []
    for s, e in cuts:
        piece = text[s:e].strip()
        if piece:
            out.append(piece)
    return out


def features(text):
    return {
        "numbers": NUM_RE.findall(text),
        "units": [m.group(2) for m in UNIT_RE.finditer(text)],
        "citations": CITE_RE.findall(text) + AUTHOR_CITE_RE.findall(text),
        "figures": FIG_RE.findall(text),
        "hedges": [w for w in HEDGE_WORDS if re.search(r"\b" + re.escape(w) + r"\b", text, re.I)],
        "negation": [m.group(0).lower() for m in NEG_RE.finditer(text)],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(json.dumps({"status": "failed", "reason": "not found"}, ensure_ascii=False))
        return 2
    with open(args.input, "r", encoding="utf-8-sig", errors="ignore") as f:
        raw = f.read().replace("\r\n", "\n")

    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    units = []
    for pi, para in enumerate(paras, start=1):
        for si, sent in enumerate(split_sentences(para), start=1):
            uid = "p%02d.s%02d" % (pi, si)
            units.append({
                "id": uid,
                "paragraph": pi,
                "original": sent,
                "protected": features(sent),
            })
    doc = {"source_file": os.path.basename(args.input), "paragraphs": len(paras),
           "units": len(units), "chars": sum(len(u["original"]) for u in units)}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"doc": doc, "units": units}, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "out": args.out, "doc": doc}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())

