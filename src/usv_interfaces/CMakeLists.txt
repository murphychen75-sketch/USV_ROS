cmake_minimum_required(VERSION 3.8)
project(usv_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED) # 新增
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED) # 新增
find_package(builtin_interfaces REQUIRED)
find_package(marine_sensor_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# 定义消息文件
set(MSG_FILES
  msg/AIVisionTarget.msg
  msg/AIVisionTargets.msg
  msg/AlarmEvent.msg
  msg/AisRaw.msg
  msg/BatteryInfo.msg
  msg/BatteryStatus.msg
  msg/BBox2D.msg
  msg/ControlDeviation.msg
  msg/DepthPosition.msg
  msg/DepthStatus.msg
  msg/DiagModuleStatus.msg
  msg/DiagResult.msg
  msg/DiagSummary.msg
  msg/FuelStatus.msg
  msg/GpsStatus.msg
  msg/ImuStatus.msg
  msg/IoDeviceStatus.msg
  msg/IoStatus.msg
  msg/OperationMode.msg
  msg/JetsonStatus.msg
  msg/HeartbeatStatus.msg
  msg/McuStatus.msg
  msg/MissionDelta.msg
  msg/MotorStatus.msg
  msg/PerceptionTrajectory.msg
  msg/PerceptionTrajectories.msg
  msg/PipelineTimestamp.msg
  msg/RadarMmObstacle.msg
  msg/RadarMmObstacles.msg
  msg/RadarNavMap.msg
  msg/RadarNavMapOrigin.msg
  msg/RadarNavScan.msg
  msg/RadarNavTarget.msg
  msg/TaskProgress.msg
  msg/TrajectoryPoint.msg
  msg/VideoStreamStatus.msg
  msg/VisionDetection.msg
  msg/VisionDetectionArray.msg
  msg/MmwaveTarget.msg
  msg/MmwaveTargetArray.msg
  msg/NavRadarTarget.msg
  msg/NavRadarTargetArray.msg
  msg/NavRadarFrame.msg
  msg/NavRadarObject.msg
  msg/AISTrack.msg
  msg/AISTrackArray.msg
  msg/GlobalTrack.msg
  msg/GlobalTrackArray.msg
  msg/VesselState.msg
  msg/WaterDepth.msg
  msg/Waypoint.msg
  msg/WaypointRoute.msg
  msg/WeatherStatus.msg
)

set(SRV_FILES
  srv/Arm.srv
  srv/AutopilotControl.srv
  srv/DiagRequest.srv
  srv/EStop.srv
  srv/IoControl.srv
  srv/ManualControl.srv
  srv/RadarNavConfig.srv
  srv/SetMode.srv
  srv/SetParams.srv
  srv/VideoControl.srv
)

set(ACTION_FILES
  action/ExecuteAutoTask.action
)

# 生成 ROS 接口代码
rosidl_generate_interfaces(${PROJECT_NAME}
  ${MSG_FILES}
  ${SRV_FILES}
  ${ACTION_FILES}
  DEPENDENCIES std_msgs geometry_msgs nav_msgs builtin_interfaces
)

# 1. 安装 C++ 头文件 (用于 C++ 节点引用常量)
install(DIRECTORY include/
  DESTINATION include
)

# 2. Python 包：勿再调用 ament_python_install_package(${PROJECT_NAME})。
# rosidl_generator_py 在 rosidl_generate_interfaces 内已对该包名调用过一次；
# 再调用会导致 ament_cmake_python_copy_* / *_egg 等 target 重复定义。
# 常量模块 topics.py 安装到与 rosidl 相同的 site-packages/${PROJECT_NAME}/。
install(FILES ${PROJECT_NAME}/topics.py
  DESTINATION ${PYTHON_INSTALL_DIR}/${PROJECT_NAME}
)

# 导出依赖
ament_export_dependencies(std_msgs geometry_msgs nav_msgs builtin_interfaces marine_sensor_msgs)
ament_export_include_directories(include)

ament_package()
