#!/usr/bin/env python3
"""绘制节点时序点亮图，并与 RTF 散点图按时间轴对齐。"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.strip())


def to_float(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return float("nan")


def load_system_metrics(path: Path) -> Tuple[List[datetime], List[float]]:
    times: List[datetime] = []
    rtf: List[float] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row.get("timestamp", "").strip()
            if not ts:
                continue
            times.append(parse_ts(ts))
            rtf.append(to_float((row.get("rtf") or "").strip()))
    return times, rtf


def load_node_activity(path: Path, active_threshold: float) -> Dict[datetime, Dict[str, bool]]:
    # timestamp -> node_name -> is_active
    status_map: Dict[datetime, Dict[str, bool]] = defaultdict(dict)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row.get("timestamp", "").strip()
            node = row.get("node_name", "").strip()
            if not ts or not node:
                continue
            activity = to_float((row.get("activity_score") or "").strip())
            status_map[parse_ts(ts)][node] = activity > active_threshold
    return status_map


def main() -> None:
    parser = argparse.ArgumentParser(description="节点点亮图 + RTF 对齐散点图")
    parser.add_argument(
        "--system-csv",
        default="monitor_logs/system_metrics.csv",
        help="系统指标 CSV 路径",
    )
    parser.add_argument(
        "--node-csv",
        default="monitor_logs/node_activity.csv",
        help="节点活跃度 CSV 路径",
    )
    parser.add_argument(
        "--active-threshold",
        type=float,
        default=0.1,
        help="节点判定为活跃的 activity_score 阈值，默认 0.1",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="monitor_logs/node_status_rtf_aligned.png",
        help="输出图片路径",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="是否弹窗显示图像（默认仅保存）",
    )
    args = parser.parse_args()

    system_csv = Path(args.system_csv)
    node_csv = Path(args.node_csv)
    if not system_csv.exists() or not node_csv.exists():
        raise SystemExit("输入 CSV 不存在，请检查 --system-csv 和 --node-csv")

    sys_times, rtf_values = load_system_metrics(system_csv)
    status_map = load_node_activity(node_csv, args.active_threshold)

    if not sys_times:
        raise SystemExit("system_metrics.csv 没有可用时间戳数据")

    # 节点固定纵坐标（全量节点，排序后固定）
    all_nodes = sorted({n for ts_map in status_map.values() for n in ts_map})
    if not all_nodes:
        raise SystemExit("node_activity.csv 没有可用节点数据")
    node_to_y = {name: idx for idx, name in enumerate(all_nodes)}

    # 仅在 system 时间轴上绘制，保证与 RTF 横轴严格对齐
    x_active: List[datetime] = []
    y_active: List[int] = []
    for ts in sys_times:
        node_status = status_map.get(ts, {})
        for node_name, is_active in node_status.items():
            if is_active:
                x_active.append(ts)
                y_active.append(node_to_y[node_name])

    fig, (ax_nodes, ax_rtf) = plt.subplots(
        2,
        1,
        figsize=(14, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [4, 1.6]},
    )

    ax_nodes.scatter(x_active, y_active, s=14, alpha=0.85, color="tab:green")
    ax_nodes.set_ylabel("Nodes")
    ax_nodes.set_title("Node Active Status (lit points)")
    ax_nodes.grid(alpha=0.25)
    ax_nodes.set_yticks(list(range(len(all_nodes))))
    ax_nodes.set_yticklabels(all_nodes, fontsize=8)

    valid_x = [t for t, v in zip(sys_times, rtf_values) if v == v]  # v==v 过滤 NaN
    valid_y = [v for v in rtf_values if v == v]
    ax_rtf.scatter(valid_x, valid_y, s=16, alpha=0.85, color="tab:red")
    ax_rtf.set_ylabel("RTF")
    ax_rtf.set_xlabel("Time")
    ax_rtf.set_title("RTF Scatter")
    ax_rtf.grid(alpha=0.3)

    locator = mdates.AutoDateLocator(minticks=6, maxticks=12)
    formatter = mdates.DateFormatter("%H:%M:%S")
    ax_rtf.xaxis.set_major_locator(locator)
    ax_rtf.xaxis.set_major_formatter(formatter)
    plt.setp(ax_rtf.get_xticklabels(), rotation=20, ha="right")

    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"[OK] 已保存图像: {args.output}")
    print(f"[INFO] 节点总数: {len(all_nodes)}，时间点: {len(sys_times)}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
