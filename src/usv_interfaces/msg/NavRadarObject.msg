std_msgs/Header header  # 标准消息头

# === 唯一标识 ===
int32 target_number  #目标批号 (0~199)
string  target_status  #目标状态（L丢失/Q获取中/T跟踪中）
# === 运动状态 (TTM报文) ===
float32 distance  #目标距离 (米)
float32 bearing  #目标方位角 (弧度)
string  bearingtr  #方位（真T/相对R）
float32 speed  #目标速度 (米每秒)
float32 course  #目标航向 (度)
string coursetr  #航向（真T/相对R）

# === 全局坐标 （TLL报文） ===
float64 latitude  #纬度 (度)
string  la_ns  #N北纬，S南纬
float64 longitude  #经度 (度)
string  lng_ns  #E东经，W西经


# === 风险评估 （TTM报文）===
float32 cpa  #最近会遇距离 (米)
float32 tcpa  #到达CPA时间 (秒)

