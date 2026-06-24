cmake_minimum_required(VERSION 3.18.1)
project("aiengine")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -mfpu=neon -mfloat-abi=softfp")

add_library(
        native-lib
        SHARED
        native-lib.cpp)

find_library(
        log-lib
        log)

target_include_directories(native-lib PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(
        native-lib
        ${log-lib})

target_compile_features(native-lib PUBLIC cxx_std_20)
