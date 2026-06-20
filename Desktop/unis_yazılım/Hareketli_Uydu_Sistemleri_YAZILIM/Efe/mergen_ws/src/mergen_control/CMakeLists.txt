cmake_minimum_required(VERSION 3.8)
project(mergen_control)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(mergen_interfaces REQUIRED)

include_directories(include)

add_library(mergen_control_core
  src/pid_controller.cpp
  src/qpd_tracker.cpp
  src/spiral_search.cpp
  src/stabilization_controller.cpp
)

add_executable(control_node src/control_node.cpp)
target_link_libraries(control_node mergen_control_core)
ament_target_dependencies(control_node rclcpp std_msgs mergen_interfaces)

install(TARGETS mergen_control_core control_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include config launch DESTINATION share/${PROJECT_NAME})

ament_package()
