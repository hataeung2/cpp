# Libraries
if (CMAKE_SYSTEM_NAME MATCHES "Windows")
    set(BUILD_SHARED_LIBS ON)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# Static library: shape
add_library(shape STATIC ../src/libs/shape.cpp)
target_link_libraries(shape PUBLIC atugcc_headers)

# Shared library: sound
add_library(sound SHARED ../src/libs/sound.cpp)
target_link_libraries(sound PUBLIC atugcc_headers)
target_compile_definitions(sound PRIVATE SOUND_EXPORTS=1)
