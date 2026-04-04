# Copyright 2026 MurphyChen
"""full_config 多船与 session_manager JSON 解析 — 供各 launch 文件共用。"""
import json
import os
import re
from typing import Optional

import yaml

from ament_index_python.packages import get_package_prefix, get_package_share_directory

ROBOT_SLOT_KEY_RE = re.compile(r'^robot_(\d+)$')


def session_manager_executable_path():
    """返回已安装的 ``session_manager`` 可执行文件路径。

    勿使用 ``ros2 run usv_sim_full session_manager`` 启动会话生成：该方式会收窄
    子进程 ``AMENT_PREFIX_PATH``，其内再调 xacro 时无法 ``$(find wamv_gazebo)`` 等
    工作区包。直接执行本路径并继承 ``ros2 launch`` 的环境即可。
    """
    prefix = get_package_prefix('usv_sim_full')
    exe = os.path.join(prefix, 'lib', 'usv_sim_full', 'session_manager')
    if not os.path.isfile(exe):
        raise FileNotFoundError(
            f'session_manager 未找到: {exe}；请先 colcon build usv_sim_full 并 source install/setup.bash'
        )
    return exe


def default_radar_nav2_param_yaml(launch_py_dir: str) -> str:
    """默认 ``radar_nav2_param.yaml`` 路径。

    优先 ``usv_sim_full/config``（与 bringup 同源，支持 ``__ROBOT_NS__`` 占位符）；
    再回退 gy_radar 源码树或已安装包。
    """
    launch_py_dir = os.path.abspath(launch_py_dir)
    share_usv = get_package_share_directory('usv_sim_full')
    candidates = [
        os.path.normpath(os.path.join(launch_py_dir, '..', 'config', 'radar_nav2_param.yaml')),
        os.path.join(share_usv, 'config', 'radar_nav2_param.yaml'),
        os.path.normpath(
            os.path.join(
                launch_py_dir,
                '..',
                '..',
                'sensor_plugins',
                'gy_radar_driver-main',
                'config',
                'radar_nav2_param.yaml',
            )
        ),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    try:
        gy = os.path.join(
            get_package_share_directory('gy_radar_driver'), 'config', 'radar_nav2_param.yaml'
        )
        if os.path.isfile(gy):
            return gy
    except Exception:
        pass
    return os.path.join(share_usv, 'config', 'radar_nav2_param.yaml')


def sorted_robot_slot_keys(cfg):
    keys = [k for k in cfg if ROBOT_SLOT_KEY_RE.match(k)]
    return sorted(keys, key=lambda k: int(ROBOT_SLOT_KEY_RE.match(k).group(1)))


def iter_all_block_sensors(cfg):
    """按 robot_1, robot_2… 展开各船 sensors；无 robot_N 时用顶层 sensors 与 robot.sensors。"""
    keys = sorted_robot_slot_keys(cfg)
    if keys:
        for k in keys:
            for s in cfg[k].get('sensors') or []:
                yield s
        return
    for s in cfg.get('sensors') or []:
        yield s
    for s in cfg.get('robot', {}).get('sensors') or []:
        yield s


def ship_config_blocks(cfg):
    keys = sorted_robot_slot_keys(cfg)
    if keys:
        return [cfg[k] for k in keys]
    rb = cfg.get('robot')
    return [rb] if isinstance(rb, dict) and rb else []


def block_has_maritime_radar(block):
    if not isinstance(block, dict):
        return False
    for s in block.get('sensors') or []:
        if not s.get('enabled', True):
            continue
        st = str(s.get('type', '')).lower()
        if st in ('maritime_radar', 'radar'):
            return True
    return False


def block_first_maritime_radar(block):
    if not isinstance(block, dict):
        return 'radar', '/sensors/radar/nav/sector'
    for s in block.get('sensors') or []:
        if not s.get('enabled', True):
            continue
        st = str(s.get('type', '')).lower()
        if st in ('maritime_radar', 'radar'):
            return str(s.get('name', 'radar')), str(
                s.get('override_topic') or '/sensors/radar/nav/sector'
            )
    return 'radar', '/sensors/radar/nav/sector'


def primary_robot_name(user_config):
    """Nav2 / RViz 等默认跟随的第一艘船名称。"""
    keys = sorted_robot_slot_keys(user_config)
    if keys:
        return str(user_config[keys[0]].get('name', 'usv_1')).strip() or 'usv_1'
    rb = user_config.get('robot') or {}
    return str(rb.get('name', 'usv_1')).strip() or 'usv_1'


def parse_session_json_from_stdout(stdout: str) -> dict:
    text = stdout.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start < 0 or end <= start:
        raise ValueError(f'session_manager 输出中未找到 JSON: {text!r}')
    return json.loads(text[start : end + 1])


def load_mmwave_sensor_defaults(full_config_path: str, user_config: dict) -> dict:
    """解析 sensor_config.yaml 中 mmwave.default，供 mmwave_4d_cloud_node 参数使用。"""
    from ament_index_python.packages import get_package_share_directory

    cfg_dir = os.path.dirname(os.path.abspath(full_config_path))
    rel = user_config.get('sensor_config_path', 'config/sensor_config.yaml')
    if os.path.isabs(rel):
        candidate = rel
    else:
        candidate = os.path.join(cfg_dir, rel)
        if not os.path.isfile(candidate):
            try:
                share = get_package_share_directory('usv_sim_full')
                candidate = os.path.join(share, rel)
            except Exception:
                pass
    if not os.path.isfile(candidate):
        return {}
    with open(candidate, 'r') as f:
        data = yaml.safe_load(f) or {}
    mm = data.get('mmwave') or {}
    return dict(mm.get('default') or {})


def mmwave_bridge_topics(sensor: dict, sanitized_ns: str):
    """与 session_manager.generate_bridge_config 中毫米波规则一致：桥接 .../points_gz，最终 .../points。"""
    st = str(sensor.get('type', '')).lower()
    if st not in ('mmwave_radar', 'mmwave'):
        return None
    sensor_name = sensor.get('name', 'mmwave')
    ros_topic = sensor.get('override_topic') or f'/sensors/mmwave/{sensor_name}/points'
    if not ros_topic.startswith('/'):
        ros_topic = '/' + ros_topic
    prefix = f'/{sanitized_ns}'
    if ros_topic.endswith('/points'):
        ros_topic_bridge = ros_topic[: -len('/points')] + '/points_gz'
    else:
        ros_topic_bridge = ros_topic + '_gz'
    input_topic = (
        ros_topic_bridge
        if ros_topic_bridge.startswith(prefix)
        else f'{prefix}{ros_topic_bridge}'
    )
    output_topic = ros_topic if ros_topic.startswith(prefix) else f'{prefix}{ros_topic}'
    return input_topic, output_topic


def _yaml_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes')
    return bool(value)


def block_enable_env_dynamics(block, default=True):
    """每船是否启动 usv_env_dynamics（风浪流外力）；缺省 true 与旧版 main 单船始终开启一致。"""
    if not isinstance(block, dict):
        return default
    return _yaml_bool(block.get('enable_env_dynamics'), default)


def block_env_dynamics_k_gains(block):
    """env_dynamics.k_wind / k_current，与 main.launch 默认一致。"""
    if not isinstance(block, dict):
        return 1.5, 250.0
    ed = block.get('env_dynamics')
    if not isinstance(ed, dict):
        return 1.5, 250.0
    return (
        float(ed.get('k_wind', 1.5)),
        float(ed.get('k_current', 250.0)),
    )


def build_mmwave_4d_cloud_parameters(mm_defs: dict, input_topic: str, output_topic: str, odom_topic: str):
    """mmwave_4d_cloud_node 参数字典（与 sensor_config mmwave.default 对齐）。"""
    md = mm_defs or {}
    return {
        'use_sim_time': True,
        'input_topic': input_topic,
        'output_topic': output_topic,
        'odom_topic': odom_topic,
        'world_frame': 'map',
        'base_rcs': float(md.get('base_rcs', 12.0)),
        'rcs_distance_decay': float(md.get('rcs_distance_decay', 0.01)),
        'perception_range_limit_m': float(md.get('perception_range_limit_m', 300.0)),
        'enable_sea_clutter': _yaml_bool(md.get('enable_sea_clutter'), False),
        'sea_clutter_probability': float(md.get('sea_clutter_probability', 0.0)),
        'sea_clutter_amplitude': float(md.get('sea_clutter_amplitude', 0.0)),
        'enable_range_measurement_error': _yaml_bool(
            md.get('enable_range_measurement_error'), False
        ),
        'enable_azimuth_measurement_error': _yaml_bool(
            md.get('enable_azimuth_measurement_error'), False
        ),
        'range_error_at_reference_m': float(md.get('range_error_at_reference_m', 0.66)),
        'range_error_reference_m': float(md.get('range_error_reference_m', 300.0)),
        'azimuth_error_std_deg': float(md.get('azimuth_error_std_deg', 0.5)),
    }


# full_config `ground_truth_sim:` 中传给 ground_truth_node 的键（排除元数据）
GROUND_TRUTH_SIM_META_KEYS = frozenset({'enabled', 'params_file'})

# 与 ground_truth_sim/config/ground_truth_params.yaml 对齐；scenario 集成时由 full_config 覆盖 frame_id/reference_*
DEFAULT_GROUND_TRUTH_NODE_PARAMS = {
    'update_dt': 0.02,
    'frame_id': 'map',
    'reference_robot': '',
    'reference_frame': 'map',
    'target_count': 5,
    'annulus_radius_min': 50.0,
    'annulus_radius_max': 500.0,
    'speed_min': 2.0,
    'speed_max': 12.0,
    'size_width_min': 2.0,
    'size_width_max': 10.0,
    'size_length_min': 5.0,
    'size_length_max': 50.0,
    'size_height_min': 2.0,
    'size_height_max': 15.0,
    'ais_match_probability': 0.4,
    'omega_noise_std': 0.005,
    'omega_decay': 0.99,
    'omega_limit': 0.1,
    'prediction_horizon': 5.0,
    'prediction_dt': 0.25,
    'history_max_points': 500,
    'rng_seed': -1,
    'tracks_topic': 'sim/ground_truth',
    'markers_topic': 'sim/ground_truth_markers',
}


def scenario_ground_truth_sim_config(user_config: dict) -> dict:
    """解析 `scenario.ground_truth_sim`；缺省 enabled=False。"""
    if not isinstance(user_config, dict):
        return {'enabled': False}
    scen = user_config.get('scenario')
    if not isinstance(scen, dict):
        return {'enabled': False}
    raw = scen.get('ground_truth_sim')
    if raw is None:
        return {'enabled': False}
    if isinstance(raw, bool):
        return {'enabled': bool(raw)}
    if not isinstance(raw, dict):
        return {'enabled': False}
    out = dict(raw)
    out['enabled'] = _yaml_bool(raw.get('enabled'), False)
    return out


def resolve_ground_truth_user_params_path(full_config_path: str, params_file) -> str:
    """ground_truth_sim.params_file 相对于 full_config 所在目录解析。"""
    if params_file is None:
        return ''
    p = str(params_file).strip()
    if not p:
        return ''
    if os.path.isabs(p):
        return p if os.path.isfile(p) else ''
    base = os.path.dirname(os.path.abspath(full_config_path))
    cand = os.path.normpath(os.path.join(base, p))
    return cand if os.path.isfile(cand) else ''


def write_ground_truth_node_params_yaml(
    gt_cfg: dict, dest_path: str, user_config: Optional[dict] = None
) -> None:
    """写入仅含 ground_truth_node/ros__parameters 的临时 YAML（scenario.ground_truth_sim）。"""
    ros_params = dict(DEFAULT_GROUND_TRUTH_NODE_PARAMS)
    for k, v in gt_cfg.items():
        if k in GROUND_TRUTH_SIM_META_KEYS:
            continue
        ros_params[k] = v
    if user_config is not None and 'reference_robot' not in gt_cfg:
        ros_params['reference_robot'] = primary_robot_name(user_config)
    payload = {'ground_truth_node': {'ros__parameters': ros_params}}
    with open(dest_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


def resolve_session_robots(session_info: dict, user_config: dict):
    """合并 session_manager 的 robots 列表；旧 JSON 无 robots 时回退单船。"""
    robots = session_info.get('robots')
    if robots:
        return robots
    rc = user_config.get('robot') or {}
    return [{
        'name': rc.get('name', 'usv'),
        'urdf_path': session_info['urdf_path'],
        'bridge_yaml_path': session_info['bridge_yaml_path'],
        'spawn_pose': rc.get('spawn_pose', [0.0, 0.0, 0.5, 0.0, 0.0, 0.0]),
    }]
