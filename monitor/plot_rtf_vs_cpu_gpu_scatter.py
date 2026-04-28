#!/usr/bin/env python3
"""在同一张图上绘制 cpu_max-rtf 与 gpu-rtf 散点图。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt


def to_float(text: str) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def load_pairs(csv_path: Path) -> Tuple[List[float], List[float], List[float]]:
    rtf_vals: List[float] = []
    cpu_vals: List[float] = []
    gpu_vals: List[float] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rtf = to_float((row.get("rtf") or "").strip())
            cpu = to_float((row.get("cpu_max_percent") or "").strip())
            gpu = to_float((row.get("gpu_util_percent") or "").strip())

            # 仅保留 rtf 有效的样本；cpu/gpu 任一有效即可参与对应散点
            if rtf != rtf:  # NaN check
                continue
            rtf_vals.append(rtf)
            cpu_vals.append(cpu)
            gpu_vals.append(gpu)

    return rtf_vals, cpu_vals, gpu_vals


def main() -> None:
    parser = argparse.ArgumentParser(description="同图绘制 cpu_max/gpu 与 rtf 的散点关系")
    parser.add_argument(
        "input_csv",
        nargs="?",
        default="monitor_logs/system_metrics.csv",
        help="输入 CSV 路径，默认 monitor_logs/system_metrics.csv",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="monitor_logs/rtf_vs_cpu_gpu_scatter.png",
        help="输出图路径，默认 monitor_logs/rtf_vs_cpu_gpu_scatter.png",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="是否弹窗显示图像",
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise SystemExit(f"输入文件不存在: {input_path}")

    rtf, cpu_max, gpu = load_pairs(input_path)
    if not rtf:
        raise SystemExit("rtf 列没有有效数据，无法绘制。")

    cpu_x = [x for x, y in zip(rtf, cpu_max) if y == y]
    cpu_y = [y for y in cpu_max if y == y]
    gpu_x = [x for x, y in zip(rtf, gpu) if y == y]
    gpu_y = [y for y in gpu if y == y]

    plt.figure(figsize=(8.5, 5.2))
    plt.scatter(cpu_x, cpu_y, s=20, alpha=0.8, c="tab:blue", label="cpu_max_percent vs rtf")
    plt.scatter(gpu_x, gpu_y, s=20, alpha=0.8, c="tab:orange", label="gpu_util_percent vs rtf")
    plt.xlabel("rtf")
    plt.ylabel("percent")
    plt.title("Scatter: CPU Max / GPU Util vs RTF")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"[OK] 已保存图像: {args.output}")
    print(f"[INFO] 点数: cpu={len(cpu_x)}, gpu={len(gpu_x)}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
