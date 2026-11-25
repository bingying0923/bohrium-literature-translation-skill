#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""归一/建图/三个查询与导出。

用法:
    python3 make_result.py --case-json /input/case.json --entities work/entities.json \
        --relations work/relations.json --out /app/output/result.json
"""
import argparse
import json
import os
import re
import sys


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def norm(surface):
    s = surface.lower().strip()
    s = re.sub(r"[-\s]+", " ", s)
    s = re.sub(r"s\b", "", s)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-json", default=None)
    ap.add_argument("--entities", required=True)
    ap.add_argument("--relations", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    ents = (load(args.entities, {}) or {}).get("entities", [])
    rels = (load(args.relations, {}) or {}).get("relations", [])

    # 归一：同 type + 同 norm 视为同一节点
    groups, nodes = {}, []
    for e in ents:
        key = (e["type"], norm(e["surface"]))
        if key in groups:
            node = groups[key]
            if e["surface"] not in node["aliases"]:
                node["aliases"].append(e["surface"])
            node["_ids"].append(e["id"])
            continue
        node = {"id": "n%03d" % (len(nodes) + 1), "type": e["type"], "surface": e["surface"],
                "canonical": e["surface"], "aliases": [e["surface"]], "anchor": e["anchor"],
                "page": e["page"], "evidence": e.get("sentence", "")[:200],
                "ambiguous": False, "merge_reason": "", "_ids": [e["id"]]}
        groups[key] = node
        nodes.append(node)

    id_map = {}
    for n in nodes:
        for oid in n["_ids"]:
            id_map[oid] = n["id"]

    # 同名不同 type 提示歧义
    by_surface = {}
    for n in nodes:
        by_surface.setdefault(norm(n["surface"]), []).append(n)
    for k, ns in by_surface.items():
        if len(ns) > 1:
            for n in ns:
                n["ambiguous"] = True

    edges, seen = [], set()
    for r in rels:
        s, t = id_map.get(r["source"]), id_map.get(r["target"])
        if not s or not t:
            continue
        key = (s, t, r["type"])
        if key in seen:
            continue
        seen.add(key)
        edges.append({"id": "e%03d" % (len(edges) + 1), "source": s, "target": t,
                      "type": r["type"], "direction": r.get("direction", "forward"),
                      "evidence": r.get("evidence", ""), "anchor": r.get("anchor", ""),
                      "strength": r.get("strength", "direct")})

    node_by_id = {n["id"]: n for n in nodes}
    queries = []
    methods = [n for n in nodes if n["type"] == "method"]
    queries.append({"q": "methods_used", "note": "本文出现的方法及其证据",
                    "answer": [{"node": m["canonical"], "anchor": m["anchor"],
                                "evidence": [e["evidence"] for e in edges if e["source"] == m["id"] or e["target"] == m["id"]][:2]}
                               for m in methods]})
    metrics = [n for n in nodes if n["type"] == "metric"]
    q2 = []
    for m in metrics:
        vals = [e["evidence"] for e in edges if e["target"] == m["id"] and e["type"] == "reports"]
        q2.append({"node": m["canonical"], "values": vals[:3], "anchor": m["anchor"]})
    queries.append({"q": "metric_values", "note": "指标的报告值与出处", "answer": q2})
    conflicts = []
    pairs = {}
    for e in edges:
        pairs.setdefault((e["source"], e["target"]), set()).add(e["type"])
    for (s, t), types in pairs.items():
        if "outperforms" in types and "limitation_of" in types:
            conflicts.append({"pair": [node_by_id[s]["canonical"], node_by_id[t]["canonical"]],
                              "types": sorted(types)})
    queries.append({"q": "conflicts", "note": "同一实体对上的矛盾关系", "answer": conflicts})

    for n in nodes:
        n.pop("_ids", None)
        if len(n["aliases"]) > 1:
            n["merge_reason"] = "同名归一：%s" % ", ".join(n["aliases"])

    weak = sum(1 for e in edges if e["strength"] == "weak")
    ambiguous = sum(1 for n in nodes if n["ambiguous"])
    unresolved = []
    if weak:
        unresolved.append({"issue": "%d 条关系证据较弱" % weak, "why": "证据句过长或跨句拼接",
                           "suggested_action": "回原文核对是否可直接支撑"})
    if ambiguous:
        unresolved.append({"issue": "%d 个同名实体未合并" % ambiguous, "why": "同名不同类型，疑似同名异义",
                           "suggested_action": "人工确认后决定是否合并"})

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": "success" if not weak and not ambiguous else "partial",
        "topic": case.get("topic", ""),
        "stats": {"nodes": len(nodes), "edges": len(edges),
                  "direct_edges": len(edges) - weak, "weak_edges": weak, "ambiguous": ambiguous},
        "nodes": nodes, "edges": edges, "queries": queries, "unresolved": unresolved,
        "artifacts": [{"path": "graph.json", "kind": "json"},
                      {"path": "queries.json", "kind": "json"}],
    }
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "graph.json"), "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "edges": edges}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "queries.json"), "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "out": args.out, "case_status": result["status"],
                      "stats": result["stats"]}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
