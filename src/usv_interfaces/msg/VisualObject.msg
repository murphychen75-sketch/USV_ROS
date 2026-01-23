std_msgs/Header header
uint32 id
string class_name           # 类别名

# === 识别框 Bounding Box ===
uint32 bbox_x               # 左上角 x (pixel)
uint32 bbox_y               # 左上角 y (pixel)
uint32 bbox_w               # 宽 (pixel)
uint32 bbox_h               # 高 (pixel)

# === 空间关系 ===
float32 relative_bearing    # 相对角度中心 (rad)
float32 confidence          # 置信度 (0.0 - 1.0)
