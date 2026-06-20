cmake_minimum_required(VERSION 3.8)
project(mergen_estimation)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(mergen_interfaces REQUIRED)

include_directories(include)

add_library(mergen_estimation_core
  src/kalman_filter.cpp
  src/quaternion_estimator.cpp
)

add_executable(imu_filter_node src/imu_filter_node.cpp)
target_link_libraries(imu_filter_node mergen_estimation_core)
ament_target_dependencies(imu_filter_node rclcpp sensor_msgs mergen_interfaces)

install(TARGETS mergen_estimation_core imu_filter_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include config launch DESTINATION share/${PROJECT_NAME})

ament_package()
