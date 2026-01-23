uint8 MODE_MANUAL        = 0  # 手动遥控
uint8 MODE_AUTO_HEADING  = 1  # 自动航向/巡线
uint8 MODE_SMART_PATH    = 2  # 智能避障巡线
uint8 MODE_AUTO_NAV      = 3  # 自主点对点导航

std_msgs/Header header
uint8 mode                    # 当前模式
