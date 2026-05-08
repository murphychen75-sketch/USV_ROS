uint32 track_id  #全局轨迹ID
float64 x  #目标X坐标（米）
float64 y  #目标Y坐标（米）
float64 v_x  #目标X方向速度（米每秒）
float64 v_y  #目标Y方向速度（米每秒）
float64 size_w  #目标宽度（米）
float64 size_l  #目标长度（米）
float64 size_h  #目标高度（米）
float64[16] covariance  #状态协方差矩阵（4x4展开）
bool is_dark_target  #是否为暗目标（无AIS等协同信息）
bool is_ais_matched  #是否已与AIS目标匹配
uint32 matched_mmsi  #匹配到的AIS MMSI编号
string source_model_name  #目标来源模型名称
