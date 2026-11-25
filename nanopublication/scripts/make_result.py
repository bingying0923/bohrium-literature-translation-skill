#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json + nanopubs.json。

用法:
    python3 make_result.py --case-json /input/case.json --claims work/claims.json \
        --bound work/bound.json --validation work/validation.json --out /app/output/result.json
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
    ap.add_argument("--case-json", default=None)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--claims", required=True)
    ap.add_argument("--bound", required=True)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    meta = load(args.meta, {}) or case.get("meta") or {}
    claims = (load(args.claims, {}) or {}).get("claims", [])
    bound = {b["id"]: b for b in (load(args.bound, {}) or {}).get("bound", [])}
    validation = load(args.validation, {}) or {}
    issues = validation.get("issues", [])

    by_claim = {}
    for i in issues:
        by_claim.setdefault(i.get("claim_id", ""), []).append(i)

    source = {
        "title": meta.get("title") or case.get("title") or "",
        "authors": meta.get("authors") or case.get("authors") or [],
        "year": meta.get("year") or case.get("year") or "",
        "version": meta.get("version") or case.get("version") or "",
        "doi": meta.get("doi") or case.get("doi") or "",
        "source_file": meta.get("source_file") or case.get("source_file") or "",
    }

    nanopubs = []
    for c in claims:
        b = bound.get(c["id"], {}).get("evidence", {})
        st = "ok"
        for i in by_claim.get(c["id"], []):
            if i["issue"] in ("weak_evidence", "evidence_number_mismatch"):
                st = i["issue"]
                break
            if i["issue"] == "overbroad":
                st = "overbroad"
            elif i["issue"] == "duplicate":
                st = "duplicate"
        if not source["title"] or not source["year"]:
            st = "missing_source" if st == "ok" else st
        nanopubs.append({
            "id": "np" + c["id"][1:],
            "assertion": {"text": c["text"], "type": c["type"],
                          "conditions": c.get("conditions", []),
                          "quantifiers": c.get("quantifiers", []),
                          "hedges": c.get("hedges", [])},
            "evidence": {"anchor": b.get("anchor", ""), "page": b.get("page"),
                         "text": b.get("text", ""), "score": b.get("score", 0),
                         "kind": b.get("kind", "weak")},
            "provenance": dict(source),
            "status": st,
        })

    stats = {
        "claims": len(nanopubs),
        "with_direct_evidence": sum(1 for n in nanopubs if n["evidence"]["kind"] == "direct"),
        "weak": sum(1 for n in nanopubs if n["status"] == "weak_evidence"),
        "overbroad": sum(1 for n in nanopubs if n["status"] == "overbroad"),
        "duplicates": sum(1 for n in nanopubs if n["status"] == "duplicate"),
    }
    status = "success" if validation.get("ok") else ("partial" if nanopubs else "failed")

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": status,
        "source": source,
        "stats": stats,
        "nanopubs": nanopubs,
        "issues": issues,
        "artifacts": [{"path": "nanopubs.json", "kind": "json"}],
    }
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "nanopubs.json"), "w", encoding="utf-8") as f:
        json.dump(nanopubs, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "out": args.out, "case_status": status, "stats": stats},
                     ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
