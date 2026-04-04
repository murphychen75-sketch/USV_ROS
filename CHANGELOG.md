# Changelog

本文件记录 **USV_ROS** 工作区面向使用者的可见变更。版本号与 Git 标签建议一致（如 `v0.1.0`）。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- 仓库根 `README.md`、`LICENSE`（Apache-2.0）、`NOTICE`（第三方摘要）。
- 文档分层：`docs_v2` 用户向 Quick Start，`docs_v1` 历史分册，`docs_v3` 架构说明；修复仿真 README 中过时链接。
- GitHub Actions：仿真相关包 `colcon build --packages-up-to usv_sim_full`（见 `.github/workflows/ci.yml`）。
- 本 `CHANGELOG.md`。

### Changed

- 统一 `usv_sim_full`、`sim_test` 的 `package.xml` 与 `setup.py` 中版本、许可证、维护者字段。
- 收紧根目录 `.gitignore`：移除对全仓库 `*.yaml` / `*.urdf` / `*.xacro` 等一刀切忽略，避免新文件被误忽略；明确忽略 `usv_sim_full` 会话日志目录。

### Fixed

- `src/usv_simulation/README.md` 中指向不存在的 `docs/QUICK_START.md` 等链接。

## [0.1.0] - 2026-04-04

首个纳入变更日志的基线版本：以 ROS 2 Humble + Gazebo Harmonic（gz）+ `usv_sim_full` 为主线的仿真工作区结构。

发版后可将下列占位链接替换为实际远程仓库地址：

- `[Unreleased]` …/compare/v0.1.0…HEAD
- `[0.1.0]` …/releases/tag/v0.1.0
