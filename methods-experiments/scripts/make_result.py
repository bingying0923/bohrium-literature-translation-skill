#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json + methods.md。

用法:
    python3 make_result.py --case-json /input/case.json --parsed work/parsed.json \
        --check work/check.json --out /app/output/result.json
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
    ap.add_argument("--parsed", required=True)
    ap.add_argument("--check", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    data = load(args.parsed, {}) or {}
    check = load(args.check, {}) or {}

    steps = data.get("steps", [])
    params = data.get("params", [])
    datasets = data.get("datasets", [])
    repro = data.get("reproduce", {})

    issues = []
    for k, v in (check.get("checks") or {}).items():
        for it in v.get("issues") or []:
            issues.append({"where": it.get("step") or it.get("name") or it.get("dataset") or k,
                           "issue": it.get("issue", k),
                           "suggested_action": "补记录或标注 not_recorded 后重跑 check_methods.py"})

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": "success" if check.get("ok") else "partial",
        "steps": steps,
        "params": params,
        "datasets": datasets,
        "reproduce": {
            "code_version": repro.get("code_version", "not_recorded"),
            "env": repro.get("env", "not_recorded"),
            "command": repro.get("command", "not_recorded"),
            "seed": repro.get("seed", "not_recorded"),
            "repeats": repro.get("repeats", "not_recorded"),
        },
        "checks": check.get("checks", {}),
        "issues": issues,
        "artifacts": [{"path": "methods.md", "kind": "markdown"}],
    }
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    md = ["# 方法与实验（%s）" % result["case_id"], "", "## 1 数据", ""]
    if datasets:
        md.append("| 数据集 | 版本 | 规模 | 划分 | 预处理 | 用途 |")
        md.append("|---|---|---|---|---|---|")
        for d in datasets:
            md.append("| %s | %s | %s | %s | %s | %s |" % (
                d.get("name", ""), d.get("version", ""), d.get("n", ""),
                d.get("split", ""), d.get("preprocess", ""), d.get("use", "")))
    else:
        md.append("（未记录数据集信息）")
    md += ["", "## 2 实验设置与复现", "",
           "- 代码版本：%s" % result["reproduce"]["code_version"],
           "- 环境：%s" % result["reproduce"]["env"],
           "- 命令：%s" % result["reproduce"]["command"],
           "- 随机种子：%s" % result["reproduce"]["seed"],
           "- 重复次数：%s" % result["reproduce"]["repeats"], "",
           "## 3 方法步骤", ""]
    for s in steps:
        md.append("%d. %s" % (s["n"], s.get("text", "")))
        if s.get("input") or s.get("output") or s.get("condition"):
            md.append("   - 输入：%s；输出：%s；条件：%s" % (
                s.get("input") or "—", s.get("output") or "—", s.get("condition") or "—"))
    md += ["", "## 4 参数", ""]
    if params:
        md.append("| 参数 | 取值 | 单位 | 作用对象 | 来源 |")
        md.append("|---|---|---|---|---|")
        for p in params:
            md.append("| %s | %s | %s | %s | %s |" % (p.get("name", ""), p.get("value", ""),
                                                      p.get("unit", ""), p.get("target", ""),
                                                      p.get("source", "")))
    else:
        md.append("（未记录参数）")
    with open(os.path.join(out_dir, "methods.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(json.dumps({"status": "ok", "out": args.out, "case_status": result["status"],
                      "steps": len(steps), "params": len(params)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
