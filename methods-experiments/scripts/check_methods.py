#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验方法与实验章节的完整性与一致性。

用法:
    python3 check_methods.py --parsed work/parsed.json [--config config.json] --out work/check.json
"""
import argparse
import json
import os
import re
import sys

NUM = re.compile(r"\d+(?:\.\d+)?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.parsed, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    steps = data.get("steps", [])
    params = data.get("params", [])
    datasets = data.get("datasets", [])
    repro = data.get("reproduce", {})

    issues = {"steps": [], "params": [], "numbers": [], "datasets": [],
              "reproduce": [], "baseline": [], "limitations": []}

    for s in steps:
        if not s.get("input") or not s.get("output"):
            issues["steps"].append({"step": s["n"], "issue": "缺 input 或 output",
                                    "text": s.get("text", "")[:60]})

    for p in params:
        if not p.get("unit"):
            issues["params"].append({"name": p.get("name"), "issue": "缺单位"})
        if not p.get("source"):
            issues["params"].append({"name": p.get("name"), "issue": "缺来源"})

    cfg_nums = set()
    if args.config and os.path.exists(args.config):
        cfg_text = open(args.config, encoding="utf-8-sig").read()
        cfg_nums = set(NUM.findall(cfg_text))
    for p in params:
        v = str(p.get("value", ""))
        if v and NUM.fullmatch(v) and cfg_nums and v not in cfg_nums:
            issues["numbers"].append({"name": p.get("name"), "value": v,
                                      "issue": "参数值与 config 中未出现，需核对来源"})

    for d in datasets:
        for field in ("name", "version", "split"):
            if not d.get(field):
                issues["datasets"].append({"dataset": d.get("name") or "(未命名)", "issue": "缺 %s" % field})

    for field in ("code_version", "env", "command"):
        if not repro.get(field):
            issues["reproduce"].append({"issue": "缺复现要素 %s" % field})
    if not repro.get("seed"):
        issues["reproduce"].append({"issue": "未记录随机种子（seed=not_recorded）"})

    if steps and not any(re.search(r"baseline|baseline|基线|对照", s.get("text", ""), re.I) for s in steps):
        issues["baseline"].append({"issue": "未描述对照/基线对象"})

    checks = {k: {"ok": not v, "issues": v} for k, v in issues.items()}
    blocking = sum(len(v) for k, v in issues.items() if k in ("steps", "params", "numbers", "datasets"))
    out = {"checks": checks, "blocking": blocking, "ok": blocking == 0}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "blocking": blocking,
                      "issues": {k: len(v) for k, v in issues.items() if v}}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
