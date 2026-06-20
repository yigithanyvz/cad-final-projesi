cmake_minimum_required(VERSION 3.8)
project(mergen_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ImuFiltered.msg"
  "msg/MotorCommand.msg"
  "msg/MotorState.msg"
  "msg/QpdReading.msg"
  "msg/SystemStatus.msg"
  "msg/TargetAngles.msg"
  "srv/SaveParameters.srv"
  "srv/SetMode.srv"
  "srv/SetTarget.srv"
)

ament_package()
