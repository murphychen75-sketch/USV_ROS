# USV_ROS Git 工作流与版本管理制度

本文定义 `USV_ROS` 主仓库的协作方式、分支规范、PR 合入门槛，以及 `usv_simulation` 作为可选仿真子模块时的使用原则。

## 1. 仓库定位

`USV_ROS` 是无人船系统的主集成仓库，目标是让 `main` 分支始终保持可构建、可部署、可回归。

主仓库保留以下内容：

- `src/usv_interfaces`：全系统统一消息、服务、动作与 topic 常量。
- `src/usv_comm`：通信基础层，例如 MAVLink、MQTT 等桥接。
- 实船运行需要的感知、融合、控制、监控、launch、config 与部署说明。
- CI、文档、开发规范、版本记录与集成层配置。

`src/usv_simulation` 定位为仿真环境，不属于实船运行的必要依赖。该目录已作为可选 submodule 管理，指向 `murphychen75-sketch/USV_Simulation`；需要仿真的开发者按需初始化，不参与实船最小部署。

## 2. 基本原则

- 禁止直接向 `main` 推送业务代码，所有改动必须通过 PR 合入。
- 每个 PR 应尽量聚焦一个功能、一个修复或一个接口变更。
- 个人分支内必须完成本地构建和最小验证后再提交 PR。
- `main` 分支只接受已经 review、可构建、说明清楚的改动。
- `build/`、`install/`、`log/`、rosbag、生成模型、临时数据和本机配置不得提交。
- 大型第三方代码、模型、数据集不直接塞入主仓；优先使用 submodule、外部下载脚本或明确的版本 pin。

## 3. 分支命名

推荐使用以下格式：

```text
feature/<name>/<topic>
fix/<name>/<topic>
interface/<name>/<topic>
sim/<name>/<topic>
docs/<name>/<topic>
```

示例：

```text
feature/chen/mqtt-status-report
fix/chen/mmwave-timeout
interface/chen/ais-msg-align
sim/chen/certificate-scenario
docs/chen/git-workflow
```

## 4. 标准开发流程

1. 更新本地主分支：

   ```bash
   git checkout main
   git pull --ff-only
   ```

2. 从最新 `main` 拉出个人分支：

   ```bash
   git checkout -b feature/<name>/<topic>
   ```

3. 在个人分支完成开发、构建和最小验证。

4. 提交 PR 到 `USV_ROS/main`。

5. PR 描述中必须说明：

   - 改动目的。
   - 影响包或节点。
   - 是否涉及接口变更。
   - 已执行的构建/验证命令。
   - 仍需注意的风险或未覆盖场景。

6. 至少一名成员 review 后再合入。

## 5. PR 前验证要求

### 5.1 普通单包改动

修改单个 ROS 2 包后，至少执行：

```bash
source /opt/ros/humble/setup.bash
colcon build --packages-select <changed_pkg> --symlink-install
```

如果该包依赖其他本仓库包，建议改用：

```bash
colcon build --packages-up-to <changed_pkg> --symlink-install
```

### 5.2 接口变更

修改 `src/usv_interfaces/msg`、`src/usv_interfaces/srv`、`src/usv_interfaces/action`、`topics.hpp` 或 `topics.py` 时，必须同步检查下游包。

最低验证：

```bash
source /opt/ros/humble/setup.bash
colcon build --packages-select usv_interfaces --symlink-install
colcon build --packages-up-to <affected_pkg> --symlink-install
```

接口 PR 应尽量单独提交，避免和业务逻辑、launch、大量重构混在一起。

### 5.3 系统级 launch/config 改动

修改系统入口、命名空间、topic、frame、参数文件或部署配置时，建议执行：

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
```

并补充对应的 `ros2 launch` 或 `ros2 run` 验证命令。

### 5.4 文档改动

仅文档改动可不要求 colcon 构建，但 PR 中应说明：

```text
验证：文档改动，无需构建。
```

## 6. `usv_simulation` 子模块策略

`usv_simulation` 只服务仿真开发和仿真验证，实船部署默认不依赖它。主仓通过 submodule 锁定其 commit 指针，远程仓库为 `git@github.com:murphychen75-sketch/USV_Simulation.git`（默认分支 `master`）。

### 6.1 默认克隆主仓

非仿真开发者可以只克隆主仓：

```bash
git clone git@github.com:murphychen75-sketch/USV_ROS.git
cd USV_ROS
```

此时不强制初始化 `src/usv_simulation`。

### 6.2 需要仿真时初始化

需要仿真环境时再执行：

```bash
git submodule update --init --recursive src/usv_simulation
```

如果首次克隆时就需要完整仿真环境，也可以使用：

```bash
git clone --recursive git@github.com:murphychen75-sketch/USV_ROS.git
```

### 6.3 仿真改动提交流程

仿真相关代码优先在 `usv_simulation` 子模块对应仓库内开发和提 PR。仿真仓 PR 合入并验证通过后，再在 `USV_ROS` 主仓中更新 submodule 指针。

主仓更新 submodule 指针时，PR 应说明：

- 更新到哪个 `usv_simulation` commit。
- 仿真仓对应 PR 或变更说明。
- 主仓中受影响的 launch/config。
- 已执行的仿真构建与运行命令。

## 7. 合入检查清单

提交 PR 前自查：

- 分支基于最新 `main`。
- 没有提交 `build/`、`install/`、`log/`、rosbag、临时文件或本机配置。
- PR 只包含本次目标相关改动。
- 已完成对应包的 `colcon build`。
- 涉及接口时已检查下游依赖。
- 涉及 launch/config 时已给出最小运行验证。
- 涉及 `usv_simulation` 时已说明是否需要更新 submodule 指针。

## 8. 推荐 PR 描述模板

~~~markdown
## 改动目的

说明为什么需要这次改动。

## 影响范围

- 影响包：
- 影响节点/launch/config：
- 是否涉及接口变更：

## 验证命令

```bash
colcon build --packages-select <pkg> --symlink-install
```

## 风险与备注

说明未覆盖场景、兼容性风险或后续工作。
~~~

