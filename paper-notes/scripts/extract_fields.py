#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从章节结构里抽论文卡片字段（每个字段必须带锚点）。

用法:
    python3 extract_fields.py --sections work/sections.json --out work/card.json
"""
import argparse
import json
import os
import re
import sys

CUE = {
    "research_question": r"\b(we (?:ask|aim|investigate|examine|test|hypothesi[sz]e|address)|this study|here we|the (?:aim|goal|objective))\b",
    "data": r"\b(samples?|dataset|participants?|patients?|subjects?|sites?|cities|cohort|n\s*=\s*\d+)\b",
    "methods": r"\b(we (?:used|measured|tested|developed|constructed)|method|assay|sensor|spectrometr|chromatograph|regression|model|protocol)\b",
    "findings": r"\b(we (?:found|observed|show|showed|report)|results? (?:show|indicate|suggest)|increase[sd]?|decrease[sd]?|higher|lower|significant)\b",
    "limitations": r"\b(limitation|caveat|future work|further stud|only|small sample|not (?:yet|been) (?:tested|validated))\b",
    "novelty": r"\b(first time|for the first time|unlike (?:previous|earlier)|previous (?:studies|work)|novel)\b",
}
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
TERM_RE = re.compile(r"\b(?:[A-Z][a-z]{2,}|[A-Z]{2,})(?:[-\s](?:[A-Z][a-z]{2,}|[A-Z]{2,})){0,2}\b")
STOP_TERM = {"The", "This", "These", "We", "Our", "In", "However", "Although", "Table", "Figure", "Fig"}


def iter_sentences(sections):
    for sec in sections:
        for para in sec["paragraphs"]:
            for si, sent in enumerate(para.get("sentences") or [para["text"]], start=1):
                yield {"section": sec["name"], "anchor": para["anchor"], "page": para["page"],
                       "sid": "%s.s%d" % (para["anchor"], si), "text": sent}


def pick(sents, cue, section_filter=None, limit=2):
    hits = []
    pat = re.compile(cue, re.I)
    for s in sents:
        if section_filter and s["section"] not in section_filter:
            continue
        if pat.search(s["text"]):
            hits.append(s)
    return hits[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.sections, "r", encoding="utf-8") as f:
        data = json.load(f)
    sections = data.get("sections", [])
    sents = list(iter_sentences(sections))

    def field(name, cue, sec_filter=None, limit=2):
        hits = pick(sents, cue, sec_filter, limit)
        if not hits:
            return {"value": "", "anchors": [], "status": "not_reported"}
        value = " ".join(h["text"] for h in hits)
        return {"value": value, "anchors": [h["anchor"] for h in hits], "status": "reported"}

    card = {
        "research_question": field("research_question", CUE["research_question"],
                                   {"Abstract", "Introduction", "Front Matter"}),
        "data": field("data", CUE["data"], {"Methods", "Abstract", "Results"}),
        "methods": field("methods", CUE["methods"], {"Methods", "Abstract"}),
        "limitations": field("limitations", CUE["limitations"],
                             {"Discussion", "Conclusion", "Limitations"}),
        "novelty": field("novelty", CUE["novelty"], {"Introduction", "Abstract", "Discussion"}),
    }

    findings = []
    for h in pick(sents, CUE["findings"], {"Results", "Abstract", "Discussion"}, limit=6):
        findings.append({"value": h["text"], "anchors": [h["anchor"]],
                         "numbers": NUM_RE.findall(h["text"])})
    card["key_findings"] = findings if findings else [
        {"value": "", "anchors": [], "numbers": [], "status": "not_reported"}]

    terms, seen = [], set()
    for s in sents:
        for m in TERM_RE.finditer(s["text"]):
            w = m.group(0).strip()
            if w in STOP_TERM or len(w) < 4:
                continue
            k = w.lower()
            if k in seen:
                continue
            seen.add(k)
            terms.append({"term": w, "anchor": s["anchor"]})
            if len(terms) >= 20:
                break
        if len(terms) >= 20:
            break
    card["terms"] = terms

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=1)

    summary = {k: (v.get("status") if isinstance(v, dict) else len(v)) for k, v in card.items()}
    print(json.dumps({"status": "ok", "out": args.out, "fields": summary}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
