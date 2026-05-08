# ROS_AIS_ws-main 运行修复记录（2026-04-27）

本文档记录本次针对 `ROS_AIS_ws-main` 的运行稳定性修复，便于后续联调、迁移与回归。

## 改动目的

- 修复 `colcon` 构建时接口包依赖顺序错误。
- 修复离线回放测试在当前环境（NumPy 2.x、未配置 DB）下无法启动的问题。
- 保持 AIS 现有节点功能逻辑不变，优先恢复可运行性。

## 改动清单

### 1) 接口包依赖长期修复

- 文件：`src/ais_reports_interfaces/package.xml`
- 变更：新增

```xml
<depend>ais_interfaces</depend>
```

原因：`ais_reports_interfaces/CMakeLists.txt` 使用了 `find_package(ais_interfaces REQUIRED)`，但 `package.xml` 未声明依赖，导致并行构建时可能先编译 `ais_reports_interfaces` 而失败。

---

### 2) 离线测试默认关闭 DB 节点（可选启用）

- 文件：`src/ais_launch/launch/setup_test.launch.py`
- 变更：
  - 新增 launch 参数：`use_db`（默认 `false`）
  - `ais_db_node` 增加条件启动：仅 `use_db:=true` 时启动

目的：避免在离线调试环境中因 `pymysql` 或数据库未部署导致整条链路失败。

---

### 3) NumPy 2.x 兼容补丁（面向第三方依赖）

- 文件：`src/ais_launch/sitecustomize.py`（新增）
- 文件：`src/ais_launch/setup.py`
- 变更：
  - `setup.py` 增加 `py_modules=['sitecustomize']`
  - `sitecustomize.py` 提供以下兼容补丁：
    - `np.float`（兼容旧 `transforms3d`）
    - `np.maximum_sctype`（兼容 NumPy 2.x 移除 API）

目的：修复 `nmea_navsat_driver` / `tf_transformations` 通过 `transforms3d` 间接触发的 NumPy 兼容崩溃。

---

### 4) 移除 `ais_tf_node` 对 `geographiclib` 的硬依赖

- 文件：`src/ais_nodes/ais_nodes/geo_utils/__init__.py`
- 变更：
  - `latlon_to_enu` / `enu_to_latlon` 改为本地切平面近似计算
  - `heading_to_enu_quaternion` 改为纯数学 yaw 四元数计算
  - 不再依赖 `geographiclib` 与 `tf_transformations`

目的：在无法安装系统 Python 包（或环境不完整）时，仍能保证 AIS TF 链路可运行。

说明：该实现适用于近场（公里级）相对态势；若未来需要高精度大范围测地计算，可恢复 `geographiclib` 方案并做参数化切换。

## 运行方式（当前推荐）

### 离线回放（默认不启 DB）

```bash
cd /home/cczh/USV_ROS/src/usv_fusion/ROS_AIS_ws-main
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

ros2 launch ais_launch setup_test.launch.py \
  bag_path:=/home/cczh/USV_ROS/src/usv_fusion/ROS_AIS_ws-main/bag_files/type1235_and_nmea_record
```

### 需要 DB 时显式启用

```bash
ros2 launch ais_launch setup_test.launch.py \
  bag_path:=/home/cczh/USV_ROS/src/usv_fusion/ROS_AIS_ws-main/bag_files/type1235_and_nmea_record \
  use_db:=true
```

## 验收建议

- 构建验证：
  - `colcon build --symlink-install`
- 运行验证：
  - `ros2 topic hz /ais_location_report`
  - `ros2 topic echo /fix --once`
  - 观察 `ais_tf_node` 日志包含 `Updated OS location` 与 `Tf vessel`

## 后续建议

- 将 `ais_launch/package.xml` 补齐运行依赖声明（如 `ais_nodes`、`nmea_navsat_driver`）。
- 按“接口统一方案2”推进：逐步把消息定义与话题常量收口到 `usv_interfaces`。
- 视部署环境决定是否恢复高精度地理转换实现。
