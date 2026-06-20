cmake_minimum_required(VERSION 3.8)
project(stewart)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(gazebo REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)

include_directories(
  ${GAZEBO_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIRS}
)

link_directories(${GAZEBO_LIBRARY_DIRS})

add_library(joint_controller SHARED plugin/joint_controller.cc)
ament_target_dependencies(joint_controller rclcpp std_msgs)
target_link_libraries(joint_controller ${GAZEBO_LIBRARIES})

add_executable(ik src/ik.cpp)
ament_target_dependencies(ik rclcpp geometry_msgs std_msgs)
target_link_libraries(ik Eigen3::Eigen)

add_executable(ps4_controller src/ps4_controller.cpp)
ament_target_dependencies(ps4_controller rclcpp geometry_msgs sensor_msgs)

add_executable(auto_motion src/auto_motion.cpp)
ament_target_dependencies(auto_motion rclcpp geometry_msgs)

set(GENERATED_SDF_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated/sdf/stewart)
file(MAKE_DIRECTORY ${GENERATED_SDF_DIR})
add_custom_command(
  OUTPUT ${GENERATED_SDF_DIR}/model.sdf
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/render_model_sdf.py
          ${CMAKE_CURRENT_SOURCE_DIR}/sdf/stewart/model.sdf.erb
          ${GENERATED_SDF_DIR}/model.sdf
  DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/scripts/render_model_sdf.py
    ${CMAKE_CURRENT_SOURCE_DIR}/sdf/stewart/model.sdf.erb
  VERBATIM
)
add_custom_target(generate_stewart_sdf ALL DEPENDS ${GENERATED_SDF_DIR}/model.sdf)

install(TARGETS
  joint_controller
  ik
  ps4_controller
  auto_motion
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch
  world
  urdf
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY
  sdf/stewart
  sdf/totalmontaj_urdf
  DESTINATION share/${PROJECT_NAME}/sdf
  FILES_MATCHING
    PATTERN "model.config"
)

install(DIRECTORY
  sdf/stewart/meshes
  DESTINATION share/${PROJECT_NAME}/sdf/stewart
)

install(DIRECTORY
  sdf/totalmontaj_urdf/meshes
  DESTINATION share/${PROJECT_NAME}/sdf/totalmontaj_urdf
)

install(FILES
  ${GENERATED_SDF_DIR}/model.sdf
  DESTINATION share/${PROJECT_NAME}/sdf/stewart
)

ament_package()
