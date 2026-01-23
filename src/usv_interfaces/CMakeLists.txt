cmake_minimum_required(VERSION 3.8)
project(usv_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED) # 新增
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# 定义消息文件
set(MSG_FILES
  msg/MmwRadarObject.msg
  msg/NavRadarObject.msg
  msg/VisualObject.msg
  msg/AisData.msg
  msg/ControlDeviation.msg
  msg/OperationMode.msg
  msg/VesselState.msg
)

set(SRV_FILES
  srv/ControlDevice.srv
)

set(ACTION_FILES
  action/ExecuteMission.action
)

# 生成 ROS 接口代码
rosidl_generate_interfaces(${PROJECT_NAME}
  ${MSG_FILES}
  ${SRV_FILES}
  ${ACTION_FILES}
  DEPENDENCIES std_msgs geometry_msgs builtin_interfaces
)

# 1. 安装 C++ 头文件 (用于 C++ 节点引用常量)
install(DIRECTORY include/
  DESTINATION include
)

# 2. 安装 Python 模块 (用于 Python 节点引用常量)
ament_python_install_package(${PROJECT_NAME})
install(DIRECTORY ${PROJECT_NAME}
  DESTINATION ${CMAKE_INSTALL_PREFIX}/${PYTHON_INSTALL_DIR}
)

# 导出依赖
ament_export_dependencies(std_msgs geometry_msgs builtin_interfaces)
ament_export_include_directories(include)

ament_package()
