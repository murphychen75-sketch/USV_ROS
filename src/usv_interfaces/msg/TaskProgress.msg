std_msgs/Header header  # 标准消息头

# 任务ID（来自 MQTT auto_task.task_id）
string task_id  # 唯一标识

# 任务状态机枚举
uint8 STATE_UNKNOWN=0  # 常量：状态值
uint8 STATE_ACCEPTED=1  # 常量：状态值、加速度
uint8 STATE_RUNNING=2  # 常量：状态值
uint8 STATE_PAUSED=3  # 常量：状态值
uint8 STATE_COMPLETED=4  # 常量：状态值
uint8 STATE_FAILED=5  # 常量：状态值
uint8 STATE_CANCELLED=6  # 常量：状态值
uint8 state  # 状态值

# 进度（0~100）
float32 progress_percent  # 进度（%）

# 当前航点索引（从0或1开始由实现约定；建议在文档中注明）
uint32 current_waypoint_index  # 电流（安）、航点信息、索引号

# 状态文本（用于上位机展示/日志）
string status_text  # 状态

# 错误信息（失败时填写）
int32 error_code  # 错误码
string message  # 消息说明

# 时间戳（毫秒，便于与 MQTT timestamp 对齐；为0表示未知/未设置）
uint64 start_time_ms  # 时间
uint64 end_time_ms  # 时间
