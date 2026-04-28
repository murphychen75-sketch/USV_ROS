#!/usr/bin/env python3
"""临时脚本：绘制文本中第二列数值散点图。"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt


def parse_second_column(file_path: Path) -> list[float]:
    values: list[float] = []
    with file_path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 2:
                print(f"[WARN] 第 {line_no} 行列数不足，已跳过: {line}")
                continue

            # 兼容 "key: value" 形式，去掉第二列中的冒号
            token = parts[1].replace(":", "").strip()
            try:
                values.append(float(token))
            except ValueError:
                print(f"[WARN] 第 {line_no} 行第二列不是数字，已跳过: {line}")

    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="绘制文本第二列数字")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="log.txt",
        help="输入文件路径，默认 log.txt",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="second_column_plot.png",
        help="输出图片路径，默认 second_column_plot.png",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="是否弹窗显示图像（默认仅保存）",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    values = parse_second_column(input_path)
    if not values:
        raise SystemExit(f"未读取到有效数字: {input_path}")

    x = list(range(len(values)))
    plt.figure(figsize=(10, 4))
    plt.scatter(x, values, s=10, alpha=0.8)
    plt.title("Second Column Scatter")
    plt.xlabel("Index")
    plt.ylabel("Value")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"[OK] 共绘制 {len(values)} 个点，已保存到: {args.output}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
