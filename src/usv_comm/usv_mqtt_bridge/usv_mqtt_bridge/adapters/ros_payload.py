"""ROS 消息与 MQTT 侧 JSON 的通用转换（去掉 header，避免时间戳/frame_id 进入载荷）。"""

from __future__ import annotations

from typing import Any, List, Mapping


def strip_headers(obj: Any) -> Any:
    """递归删除字典树中键名为 ``header`` 的节点。"""
    if isinstance(obj, Mapping):
        return {
            k: strip_headers(v)
            for k, v in obj.items()
            if k != "header"
        }
    if isinstance(obj, (list, tuple)):
        seq: List[Any] = obj if isinstance(obj, list) else list(obj)
        return [strip_headers(x) for x in seq]
    return obj
