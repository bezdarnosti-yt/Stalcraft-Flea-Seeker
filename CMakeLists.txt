cmake_minimum_required(VERSION 3.10.0)
project(stalcraft-flea-seeker VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

file(GLOB SRC "${CMAKE_SOURCE_DIR}/src/*.cpp")
file(GLOB INCL "${CMAKE_SOURCE_DIR}/include/*.h")

include(FetchContent)

FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG        v3.12.0
    GIT_SHALLOW    TRUE   # только последний коммит тега, без истории
)

FetchContent_Declare(
    spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG        v1.17.0
    GIT_SHALLOW    TRUE
)

FetchContent_MakeAvailable(nlohmann_json spdlog)

find_package(Qt6 REQUIRED COMPONENTS
    Core Widgets Network WebEngineWidgets WebChannel)

add_executable(${PROJECT_NAME} ${SRC})

target_include_directories(${PROJECT_NAME} PRIVATE 
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt6::Core
    Qt6::Widgets
    Qt6::Network
    Qt6::WebEngineWidgets
    Qt6::WebChannel
    nlohmann_json::nlohmann_json
)