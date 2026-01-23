std_msgs/Header header

float32 cross_track_error   # 循迹误差 (偏航距离 m, 左正右负)
float32 heading_error       # 艏向误差 (rad)
float32 distance_to_goal    # 距离当前局部目标点的距离 (m)
float32 target_speed        # 期望航速 (m/s)
float32 current_speed       # 实际航速 (m/s)
