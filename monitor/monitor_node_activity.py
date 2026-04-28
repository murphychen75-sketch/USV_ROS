#!/usr/bin/env python3
"""
实时采样 ROS2 节点活跃度、RTF、CPU 与 GPU，并输出关联分析。

输出文件：
- system_metrics.csv: 系统级时序数据
- node_activity.csv: 节点级时序数据
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import re
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import psutil
except ImportError as exc:
    raise SystemExit(
        "缺少依赖 psutil，请先安装：python3 -m pip install psutil"
    ) from exc


REAL_TIME_FACTOR_RE = re.compile(r"real_time_factor[:=\s]+([0-9]*\.?[0-9]+)")
NODE_ARG_RE = re.compile(r"__node:=([A-Za-z0-9_/.-]+)")


def run_command(cmd: List[str], timeout: float = 1.0) -> str:
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def parse_rtf_from_text(text: str) -> Optional[float]:
    if not text:
        return None
    match = REAL_TIME_FACTOR_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def read_latest_rtf_from_log(log_file: Path) -> Optional[float]:
    if not log_file.exists():
        return None
    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in reversed(lines[-300:]):
        value = parse_rtf_from_text(line)
        if value is not None:
            return value
    return None


def read_rtf(args: argparse.Namespace) -> Optional[float]:
    if args.rtf_source == "gz":
        # 兼容当前 gz CLI（无 "gz stats" 子命令）：
        # 优先从 /stats topic 读一帧，失败后再尝试 world 级 stats。
        out = run_command(["gz", "topic", "-e", "-n", "1", "-t", "/stats"], timeout=1.5)
        value = parse_rtf_from_text(out)
        if value is not None:
            return value

        # 某些场景仅有 /world/<name>/stats
        topic_list = run_command(["gz", "topic", "-l"], timeout=1.2)
        for line in topic_list.splitlines():
            topic = line.strip()
            if topic.startswith("/world/") and topic.endswith("/stats"):
                out = run_command(
                    ["gz", "topic", "-e", "-n", "1", "-t", topic],
                    timeout=1.5,
                )
                value = parse_rtf_from_text(out)
                if value is not None:
                    return value
        return None
    if args.rtf_source == "log":
        if not args.rtf_log:
            return None
        return read_latest_rtf_from_log(Path(args.rtf_log))
    return None


def read_gpu_util() -> Optional[float]:
    out = run_command(
        [
            "nvidia-smi",
            "--query-gpu=utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        timeout=0.8,
    )
    if not out:
        return None
    vals: List[float] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            vals.append(float(line))
        except ValueError:
            continue
    if not vals:
        return None
    return max(vals)


def list_ros_nodes() -> List[str]:
    out = run_command(["ros2", "node", "list"], timeout=1.2)
    if not out:
        return []
    nodes = [line.strip() for line in out.splitlines() if line.strip()]
    return sorted(set(nodes))


def extract_ros_node_names(proc: psutil.Process) -> List[str]:
    try:
        cmdline = proc.cmdline()
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        return []
    joined = " ".join(cmdline)
    names = NODE_ARG_RE.findall(joined)
    unique = sorted(set(name if name.startswith("/") else f"/{name}" for name in names))
    return unique


def collect_node_activity(nodes_from_graph: List[str]) -> List[Dict[str, object]]:
    node_rows: List[Dict[str, object]] = []
    node_set = set(nodes_from_graph)

    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        names = extract_ros_node_names(proc)
        if not names:
            continue
        try:
            cpu_percent = proc.cpu_percent(interval=None)
            mem_mb = proc.memory_info().rss / (1024.0 * 1024.0)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        for node_name in names:
            # 只统计 ROS 图上出现的节点；若 ros2 node list 失败，退化为全量。
            if node_set and node_name not in node_set:
                continue
            activity_score = cpu_percent
            node_rows.append(
                {
                    "node_name": node_name,
                    "pid": proc.pid,
                    "cpu_percent": round(cpu_percent, 3),
                    "memory_mb": round(mem_mb, 3),
                    "activity_score": round(activity_score, 3),
                }
            )
    return node_rows


def safe_float(v: Optional[float]) -> float:
    if v is None or math.isnan(v):
        return float("nan")
    return float(v)


def pearson_corr(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 3 or len(xs) != len(ys):
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


def ensure_csv_with_header(path: Path, header: List[str]) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def append_row(path: Path, row: List[object]) -> None:
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


class StopFlag:
    def __init__(self) -> None:
        self.stop = False

    def _handler(self, signum: int, frame: object) -> None:
        del signum, frame
        self.stop = True

    def install(self) -> None:
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="实时记录 ROS 节点活跃度、RTF、CPU 峰值与 GPU 占用"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="采样周期（秒），默认 1.0",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="采样总时长（秒）；0 表示持续运行直到 Ctrl+C",
    )
    parser.add_argument(
        "--output-dir",
        default="monitor_logs",
        help="输出目录，默认 monitor_logs",
    )
    parser.add_argument(
        "--rtf-source",
        choices=["gz", "log", "none"],
        default="gz",
        help="RTF 来源：gz/log/none，默认 gz",
    )
    parser.add_argument(
        "--rtf-log",
        default="log.txt",
        help="当 --rtf-source=log 时读取的日志文件，默认 log.txt",
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=5,
        help="每 N 次采样打印一次摘要，默认 5",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    system_csv = output_dir / "system_metrics.csv"
    node_csv = output_dir / "node_activity.csv"

    ensure_csv_with_header(
        system_csv,
        [
            "timestamp",
            "rtf",
            "cpu_max_percent",
            "cpu_avg_percent",
            "gpu_util_percent",
            "ros_node_count",
            "active_node_count",
            "active_cpu_sum",
        ],
    )
    ensure_csv_with_header(
        node_csv,
        [
            "timestamp",
            "node_name",
            "pid",
            "cpu_percent",
            "memory_mb",
            "activity_score",
        ],
    )

    # 先预热一次，避免第一次 cpu_percent 全是 0
    for p in psutil.process_iter():
        try:
            p.cpu_percent(interval=None)
        except Exception:
            continue
    psutil.cpu_percent(interval=None, percpu=True)

    stop_flag = StopFlag()
    stop_flag.install()

    print("[INFO] 开始采样，按 Ctrl+C 停止")
    print(f"[INFO] 输出目录: {output_dir.resolve()}")
    print(f"[INFO] RTF 来源: {args.rtf_source}")

    start_time = time.time()
    sample_idx = 0

    rtf_hist: List[float] = []
    cpu_max_hist: List[float] = []
    gpu_hist: List[float] = []
    active_sum_hist: List[float] = []

    while not stop_flag.stop:
        tick_start = time.time()
        now = dt.datetime.now().isoformat(timespec="seconds")

        ros_nodes = list_ros_nodes()
        node_rows = collect_node_activity(ros_nodes)

        cpu_all = psutil.cpu_percent(interval=None, percpu=True)
        cpu_max = max(cpu_all) if cpu_all else float("nan")
        cpu_avg = sum(cpu_all) / len(cpu_all) if cpu_all else float("nan")
        gpu_util = read_gpu_util()
        rtf = read_rtf(args)

        active_nodes = [r for r in node_rows if float(r["activity_score"]) > 0.0]
        active_cpu_sum = sum(float(r["cpu_percent"]) for r in active_nodes)

        append_row(
            system_csv,
            [
                now,
                "" if rtf is None else f"{rtf:.6f}",
                f"{cpu_max:.3f}" if not math.isnan(cpu_max) else "",
                f"{cpu_avg:.3f}" if not math.isnan(cpu_avg) else "",
                "" if gpu_util is None else f"{gpu_util:.3f}",
                len(ros_nodes),
                len(active_nodes),
                f"{active_cpu_sum:.3f}",
            ],
        )
        for row in node_rows:
            append_row(
                node_csv,
                [
                    now,
                    row["node_name"],
                    row["pid"],
                    row["cpu_percent"],
                    row["memory_mb"],
                    row["activity_score"],
                ],
            )

        rtf_hist.append(safe_float(rtf))
        cpu_max_hist.append(safe_float(cpu_max))
        gpu_hist.append(safe_float(gpu_util))
        active_sum_hist.append(safe_float(active_cpu_sum))

        sample_idx += 1
        if args.print_every > 0 and sample_idx % args.print_every == 0:
            corr_cpu = pearson_corr(rtf_hist, cpu_max_hist)
            corr_gpu = pearson_corr(rtf_hist, gpu_hist)
            corr_active = pearson_corr(rtf_hist, active_sum_hist)
            print(
                f"[{now}] sample={sample_idx} "
                f"rtf={rtf if rtf is not None else 'NA'} "
                f"cpu_max={cpu_max:.1f}% gpu={gpu_util if gpu_util is not None else 'NA'}% "
                f"active_nodes={len(active_nodes)} "
                f"corr(rtf,cpu_max)={corr_cpu if corr_cpu is not None else 'NA'} "
                f"corr(rtf,gpu)={corr_gpu if corr_gpu is not None else 'NA'} "
                f"corr(rtf,active_cpu_sum)={corr_active if corr_active is not None else 'NA'}"
            )

        if args.duration > 0 and (time.time() - start_time) >= args.duration:
            break

        elapsed = time.time() - tick_start
        sleep_time = args.interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    print("[INFO] 采样结束")
    print(f"[INFO] 系统指标: {system_csv.resolve()}")
    print(f"[INFO] 节点活跃度: {node_csv.resolve()}")


if __name__ == "__main__":
    main()
