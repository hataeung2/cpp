# Sample libraries (task 040-01): how a static and a shared library are built and linked.
# They are build examples, not framework libraries; those live in libs/<name>/ (docs/lib_candidates.md).
if (CMAKE_SYSTEM_NAME MATCHES "Windows")
    set(BUILD_SHARED_LIBS ON)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# Static library: shape
add_library(shape STATIC shape.cpp)
target_link_libraries(shape PUBLIC atugcc_headers)

# Shared library: sound
add_library(sound SHARED sound.cpp)
target_link_libraries(sound PUBLIC atugcc_headers)
target_compile_definitions(sound PRIVATE SOUND_EXPORTS=1)
