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
