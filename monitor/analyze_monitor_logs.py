#!/usr/bin/env python3
"""
离线分析 monitor_node_activity.py 采样结果，定位与 RTF 低谷相关的节点。
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def to_float(v: str) -> float:
    if v is None:
        return float("nan")
    s = str(v).strip()
    if not s:
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    pairs = [(x, y) for x, y in zip(xs, ys) if not (math.isnan(x) or math.isnan(y))]
    if len(pairs) < 3:
        return None
    px = [p[0] for p in pairs]
    py = [p[1] for p in pairs]
    try:
        return statistics.correlation(px, py)
    except statistics.StatisticsError:
        return None


def read_system_metrics(path: Path) -> Tuple[List[str], Dict[str, List[float]]]:
    timestamps: List[str] = []
    cols: Dict[str, List[float]] = {
        "rtf": [],
        "cpu_max_percent": [],
        "cpu_avg_percent": [],
        "gpu_util_percent": [],
        "active_cpu_sum": [],
    }
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamps.append(row.get("timestamp", ""))
            for key in cols:
                cols[key].append(to_float(row.get(key, "")))
    return timestamps, cols


def read_node_activity(path: Path) -> Dict[str, Dict[str, float]]:
    # timestamp -> node_name -> cpu_percent
    node_cpu_by_ts: Dict[str, Dict[str, float]] = defaultdict(dict)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row.get("timestamp", "")
            node = row.get("node_name", "")
            cpu = to_float(row.get("cpu_percent", ""))
            if not ts or not node or math.isnan(cpu):
                continue
            node_cpu_by_ts[ts][node] = cpu
    return node_cpu_by_ts


def percentile(values: List[float], q: float) -> Optional[float]:
    vals = sorted(v for v in values if not math.isnan(v))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    idx = (len(vals) - 1) * q
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return vals[lo]
    frac = idx - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def safe_fmt(v: Optional[float], nd: int = 4) -> str:
    if v is None or math.isnan(v):
        return "NA"
    return f"{v:.{nd}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="分析节点活跃度与 RTF 关联")
    parser.add_argument(
        "--input-dir",
        default="monitor_logs",
        help="输入目录（包含 system_metrics.csv 和 node_activity.csv）",
    )
    parser.add_argument(
        "--low-rtf-threshold",
        type=float,
        default=-1.0,
        help="低 RTF 阈值；<0 时自动用 RTF P25",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=12,
        help="输出可疑节点 TopK，默认 12",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    system_csv = input_dir / "system_metrics.csv"
    node_csv = input_dir / "node_activity.csv"
    if not system_csv.exists() or not node_csv.exists():
        raise SystemExit(
            f"输入文件不存在，请确认目录: {input_dir} 下有 system_metrics.csv 和 node_activity.csv"
        )

    timestamps, sys_cols = read_system_metrics(system_csv)
    node_cpu_by_ts = read_node_activity(node_csv)

    rtf = sys_cols["rtf"]
    rtf_valid = [v for v in rtf if not math.isnan(v)]
    if len(rtf_valid) < 3:
        raise SystemExit("RTF 有效数据不足，无法分析。")

    auto_threshold = percentile(rtf, 0.25)
    low_threshold = args.low_rtf_threshold if args.low_rtf_threshold >= 0 else (auto_threshold or 0.2)
    low_mask = [(not math.isnan(v)) and v <= low_threshold for v in rtf]
    low_cnt = sum(1 for x in low_mask if x)
    if low_cnt == 0:
        raise SystemExit(f"未检测到低谷样本，当前阈值={low_threshold:.4f}")

    # 系统级相关性
    corr_cpu_max = pearson(rtf, sys_cols["cpu_max_percent"])
    corr_cpu_avg = pearson(rtf, sys_cols["cpu_avg_percent"])
    corr_gpu = pearson(rtf, sys_cols["gpu_util_percent"])
    corr_active = pearson(rtf, sys_cols["active_cpu_sum"])

    # 节点全集
    all_nodes = sorted({node for ts in node_cpu_by_ts.values() for node in ts.keys()})
    if not all_nodes:
        raise SystemExit("node_activity.csv 中没有有效节点数据。")

    per_node_scores = []
    for node in all_nodes:
        node_series: List[float] = []
        for ts in timestamps:
            node_series.append(node_cpu_by_ts.get(ts, {}).get(node, 0.0))

        corr = pearson(rtf, node_series)
        # 低谷时均值 vs 非低谷均值
        low_vals = [x for x, is_low in zip(node_series, low_mask) if is_low]
        high_vals = [x for x, is_low in zip(node_series, low_mask) if not is_low]
        low_mean = statistics.fmean(low_vals) if low_vals else 0.0
        high_mean = statistics.fmean(high_vals) if high_vals else 0.0
        delta = low_mean - high_mean
        # 可疑评分：低谷上升越明显 + 与 rtf 负相关越强 => 分数越高
        neg_corr = 0.0
        if corr is not None and corr < 0:
            neg_corr = -corr
        score = (delta if delta > 0 else 0.0) * (1.0 + neg_corr)
        per_node_scores.append(
            {
                "node": node,
                "score": score,
                "corr_rtf": corr,
                "low_mean_cpu": low_mean,
                "high_mean_cpu": high_mean,
                "delta_cpu": delta,
            }
        )

    per_node_scores.sort(key=lambda x: x["score"], reverse=True)
    top = per_node_scores[: max(1, args.top_k)]

    print("=== RTF 低谷关联分析 ===")
    print(f"输入目录: {input_dir.resolve()}")
    print(f"样本数: {len(timestamps)}")
    print(f"RTF 低谷阈值: {low_threshold:.4f} (低谷样本 {low_cnt}/{len(timestamps)})")
    print("")
    print("系统级相关性 (Pearson):")
    print(f"- corr(rtf, cpu_max)        = {safe_fmt(corr_cpu_max)}")
    print(f"- corr(rtf, cpu_avg)        = {safe_fmt(corr_cpu_avg)}")
    print(f"- corr(rtf, gpu_util)       = {safe_fmt(corr_gpu)}")
    print(f"- corr(rtf, active_cpu_sum) = {safe_fmt(corr_active)}")
    print("")
    print(f"可疑节点 Top {len(top)} (按低谷影响评分):")
    print("node, score, corr_rtf, low_mean_cpu, high_mean_cpu, delta_cpu")
    for item in top:
        print(
            f"{item['node']}, "
            f"{safe_fmt(item['score'])}, "
            f"{safe_fmt(item['corr_rtf'])}, "
            f"{safe_fmt(item['low_mean_cpu'])}, "
            f"{safe_fmt(item['high_mean_cpu'])}, "
            f"{safe_fmt(item['delta_cpu'])}"
        )


if __name__ == "__main__":
    main()
