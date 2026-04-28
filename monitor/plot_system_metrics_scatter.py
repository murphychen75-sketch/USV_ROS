#!/usr/bin/env python3
"""将 system_metrics.csv 的数值列绘制为散点图子图。"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt

RTF_RE = re.compile(r"real_time_factor[:=\s]+([0-9]*\.?[0-9]+)")


def is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def read_numeric_columns(csv_path: Path) -> Dict[str, List[float]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"CSV 表头为空: {csv_path}")

        # 默认跳过 timestamp，其他列尝试按浮点数读取
        candidate_fields = [name for name in reader.fieldnames if name != "timestamp"]
        columns: Dict[str, List[float]] = {name: [] for name in candidate_fields}

        for row in reader:
            for name in candidate_fields:
                v = (row.get(name) or "").strip()
                if not v or not is_float(v):
                    columns[name].append(float("nan"))
                else:
                    columns[name].append(float(v))

    # 仅保留至少有一个有效值的列
    valid_columns = {
        k: v for k, v in columns.items() if any(not math.isnan(x) for x in v)
    }
    if not valid_columns:
        raise SystemExit(f"没有可绘制的数值列: {csv_path}")
    return valid_columns


def read_rtf_from_log(log_path: Path) -> List[float]:
    if not log_path.exists():
        return []
    values: List[float] = []
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = RTF_RE.search(line)
        if not m:
            continue
        try:
            values.append(float(m.group(1)))
        except ValueError:
            continue
    return values


def draw_combined_rtf_ros_node_scatter(
    data: Dict[str, List[float]], output_path: Path, rtf_fallback: List[float]
) -> None:
    if "ros_node_count" not in data:
        print("[WARN] 未找到 ros_node_count 列，跳过 rtf+ros_node_count 同图输出。")
        return

    rtf_series = data.get("rtf", [])
    has_rtf = any(not math.isnan(v) for v in rtf_series)

    ros_series = data["ros_node_count"]
    n = len(ros_series)
    x = list(range(n))

    if not has_rtf:
        if not rtf_fallback:
            print("[WARN] CSV 中 rtf 全为空，且未提供可用 fallback，无法绘制同图。")
            return
        k = min(n, len(rtf_fallback))
        ros_series = ros_series[:k]
        rtf_series = rtf_fallback[:k]
        x = list(range(k))
        print(f"[INFO] rtf 为空，已使用 fallback rtf（{k} 个点）进行同图绘制。")

    fig, ax1 = plt.subplots(figsize=(12, 4.2))
    ax2 = ax1.twinx()

    ax1.scatter(x, ros_series, s=14, alpha=0.75, c="tab:blue", label="ros_node_count")
    ax2.scatter(x, rtf_series, s=14, alpha=0.75, c="tab:red", label="rtf")

    ax1.set_xlabel("Sample Index")
    ax1.set_ylabel("ros_node_count", color="tab:blue")
    ax2.set_ylabel("rtf", color="tab:red")
    ax1.grid(alpha=0.3)
    plt.title("ros_node_count & rtf Scatter (Dual Y-Axis)")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"[OK] 已保存同图散点: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="绘制 system_metrics.csv 散点图")
    parser.add_argument(
        "input_csv",
        nargs="?",
        default="monitor_logs/system_metrics.csv",
        help="输入 CSV，默认 monitor_logs/system_metrics.csv",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="monitor_logs/system_metrics_scatter.png",
        help="输出图片路径，默认 monitor_logs/system_metrics_scatter.png",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="弹窗显示图像（默认仅保存）",
    )
    parser.add_argument(
        "--combined-output",
        default="monitor_logs/rtf_ros_node_scatter.png",
        help="rtf 与 ros_node_count 同图输出路径",
    )
    parser.add_argument(
        "--rtf-log-fallback",
        default="log.txt",
        help="当 CSV 的 rtf 列为空时，使用该日志解析 rtf 作为 fallback",
    )
    args = parser.parse_args()

    csv_path = Path(args.input_csv)
    if not csv_path.exists():
        raise SystemExit(f"输入文件不存在: {csv_path}")

    data = read_numeric_columns(csv_path)
    n = len(next(iter(data.values())))
    x = list(range(n))

    cols = list(data.keys())
    fig, axes = plt.subplots(len(cols), 1, figsize=(12, 2.8 * len(cols)), sharex=True)
    if len(cols) == 1:
        axes = [axes]

    for ax, col_name in zip(axes, cols):
        y = data[col_name]
        ax.scatter(x, y, s=12, alpha=0.8)
        ax.set_ylabel(col_name)
        ax.grid(alpha=0.3)

    axes[-1].set_xlabel("Sample Index")
    fig.suptitle("System Metrics Scatter Plots", fontsize=14)
    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"[OK] 已保存散点图: {args.output}")
    draw_combined_rtf_ros_node_scatter(
        data=data,
        output_path=Path(args.combined_output),
        rtf_fallback=read_rtf_from_log(Path(args.rtf_log_fallback)),
    )

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
