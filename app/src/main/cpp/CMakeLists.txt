cmake_minimum_required(VERSION 3.22.1)
project(assetwright_meshopt LANGUAGES CXX)
add_library(assetwright_meshopt SHARED
    meshopt_jni.cpp
    indexcodec.cpp
    vertexcodec.cpp
    vertexfilter.cpp
)
target_compile_features(assetwright_meshopt PRIVATE cxx_std_11)
target_compile_options(assetwright_meshopt PRIVATE -O3 -fvisibility=hidden)
target_link_libraries(assetwright_meshopt log)

include(FetchContent)
set(DRACO_GLTF_BITSTREAM ON CACHE BOOL "Build Draco for glTF")
set(DRACO_INSTALL OFF CACHE BOOL "Skip standalone Draco installation")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
FetchContent_Declare(draco
    URL https://codeload.github.com/google/draco/tar.gz/8786740086a9f4d83f44aa83badfbea4dce7a1b5
    URL_HASH SHA256=b9c2392dbfcf454aaec68823d832de9d62614054b33807b7c9776799b8e0bbca
)
FetchContent_MakeAvailable(draco)

add_library(assetwright_draco SHARED draco_jni.cpp)
target_compile_features(assetwright_draco PRIVATE cxx_std_17)
target_include_directories(assetwright_draco PRIVATE "${draco_SOURCE_DIR}/src" "${CMAKE_BINARY_DIR}")
target_link_libraries(assetwright_draco PRIVATE draco::draco)
