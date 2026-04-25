# target_ship `10m.dae` 缩放测试

该测试环境用于验证 `description/models/target_ship/10m.dae` 在 Gazebo Sim 中的实际缩放效果，并直观看到：

- `visual mesh` 的 `scale` 是否按预期生效
- 同步更新 collision 时，包络盒如何随之变化
- 只缩放 visual、不缩放 collision 时，会产生怎样的外形/碰撞不一致
- 非等比缩放 `1 0.75 1.25` 的效果

## 运行方式

```bash
cd /home/cczh/USV_ROS
colcon build --packages-select usv_sim_full --symlink-install
source install/setup.bash
ros2 launch usv_sim_full target_ship_scale_test.launch.py
```

如需打印 GZ 资源路径：

```bash
ros2 launch usv_sim_full target_ship_scale_test.launch.py verbose_launch:=true
```

## 场景布局

世界文件：`worlds/target_ship_scale_test.sdf`

上排（`y=12`）是 **collision 与 visual 同步缩放**：

- `x=-24`：`scale = 0.5 0.5 0.5`
- `x=0`：`scale = 1 1 1`
- `x=28`：`scale = 2 2 2`

下排（`y=-14`）是对照组：

- `x=0`：`visual` 使用 `scale = 2 2 2`，但 collision 保持 `1x`
- `x=28`：`visual/collision` 同步使用 `scale = 1 0.75 1.25`

第三排（`y=-40`）是 **`10m_collosion.md` 拟合的 compound box 首版**：

- 使用 `description/models/target_ship/10m_mesh_profile.yaml`
- 局部坐标约定：`x=船尾到船首`，`y=左右对称宽度中心线`，`z=高度`
- 初始整体偏移：`[+0.000503, 0, 0]`
- mesh pose 修正：`xyz=[0.000503, 0, 0.02260607]`, `rpy=[+90deg, 0, -90deg]`

每艘船外面都有一个半透明包络盒：

- 红色：`0.5x`
- 绿色：`1x`
- 蓝色：`2x`
- 黄色：`visual-only 2x`
- 紫色：`1 0.75 1.25`

## 模型轴向说明

通过读取 `10m.dae` 顶点包围盒得到原始 mesh 尺寸约为：

- `x = 3.6`
- `y = 2.93260607`
- `z = 9.898994`

该模型的长轴在原始 `z` 方向，因此测试里统一对 mesh 增加：

- `roll = +90deg`

让船体长轴落到地面平面内；同时根据原始 bbox 的最小值补偿了 `y/z` 平移，使船底正好贴地。

## 如何观察

1. 比较上排三艘船的长度、宽度和高度是否按比例变化。
2. 对比下排左侧黄色包络盒与 2x 船模，观察“只缩放 visual，不缩放 collision”的效果。
3. 对比下排右侧紫色船模，观察非等比缩放是否会导致视觉形态不自然。
4. 对比第三排的 4 段碰撞盒和船体外轮廓，重点观察：
   - 船尾和船首是否需要整体前后平移
   - 各段顶面对齐是否合理
   - `y=0` 对称中心线是否与船体中线吻合
   - 是否需要统一上抬或下压整组碰撞盒

## 后续接入建议

若后续把 `ground_truth_gazebo_models_node` 从长方体切到 `dae`：

- `visual` 可直接复用这里的 mesh + pose 偏置思路
- `collision` 建议继续使用简化 box / compound box
- `GlobalTrack.size_l/size_w/size_h` 建议绑定到物理包络盒，而不是直接绑定原始 mesh 顶点尺寸
