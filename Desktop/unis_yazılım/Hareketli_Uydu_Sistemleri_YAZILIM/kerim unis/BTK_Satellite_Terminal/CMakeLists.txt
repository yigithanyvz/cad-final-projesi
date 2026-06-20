cmake_minimum_required(VERSION 3.16)
project(satellite_tracker CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ─── Hedef seç ────────────────────────────────────────────
# PC simülasyonu için:  cmake -DTARGET=SIM ..
# STM32 için cross-compile toolchain dosyası kullanın.

option(USE_FREERTOS "FreeRTOS desteğini etkinleştir" OFF)
option(TARGET_SIM   "PC simülasyon modu"             ON)

include_directories(include)

find_package(ament_cmake QUIET)
if(ament_cmake_FOUND)
    find_package(rclcpp REQUIRED)
    find_package(sensor_msgs REQUIRED)
    find_package(std_msgs REQUIRED)
endif()

set(SOURCES
    src/main.cpp
    src/PIDController.cpp
    src/SensorFusion.cpp
    src/SatelliteTracker.cpp
    src/StabilizationController.cpp
    src/CameraObjectDetector.cpp
    src/LaserTracker.cpp
    src/initialization.cpp
    src/telemetry.cpp
)

set(ALGORITHM_SOURCES
    src/PIDController.cpp
    src/SensorFusion.cpp
    src/SatelliteTracker.cpp
    src/StabilizationController.cpp
    src/CameraObjectDetector.cpp
    src/LaserTracker.cpp
)

add_executable(satellite_tracker ${SOURCES})

target_compile_options(satellite_tracker PRIVATE
    -Wall -Wextra -O2
)

if(USE_FREERTOS)
    target_compile_definitions(satellite_tracker PRIVATE USE_FREERTOS)
    # FreeRTOS kaynaklarını buraya ekleyin
endif()

# ─── Test / Simülasyon ────────────────────────────────────
if(TARGET_SIM)
    target_compile_definitions(satellite_tracker PRIVATE SIM_MODE)
endif()

if(ament_cmake_FOUND)
    add_executable(satellite_tracker_ros2_node
        src/ros2_algorithm_node.cpp
        ${ALGORITHM_SOURCES}
    )
    target_compile_options(satellite_tracker_ros2_node PRIVATE
        -Wall -Wextra -O2
    )
    target_include_directories(satellite_tracker_ros2_node PRIVATE include)
    ament_target_dependencies(satellite_tracker_ros2_node
        rclcpp
        sensor_msgs
        std_msgs
    )

    install(TARGETS
        satellite_tracker
        satellite_tracker_ros2_node
        DESTINATION lib/${PROJECT_NAME}
    )

    ament_package()
endif()
