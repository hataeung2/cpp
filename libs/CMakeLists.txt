## common settings
if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
    # dynamic
    set(BUILD_SHARED_LIBS ON)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()
##!common settings


## external libraries
include(FetchContent)
# @ fmt
FetchContent_Declare(
  fmt
  GIT_REPOSITORY "https://github.com/fmtlib/fmt"
  GIT_TAG "10.1.1"
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/dependencies/fmt
)
FetchContent_MakeAvailable(fmt)
##!external libraries


# @ samples
# source to binary file
add_library(shape STATIC libsample/shape.cpp)
add_library(sound SHARED libsample/sound.cpp)
# dependency set
target_link_libraries(shape PRIVATE fmt)
target_link_libraries(sound PRIVATE fmt)
# compile definition
target_compile_definitions(sound PRIVATE SOUND_EXPORTS=1)
# include path
target_include_directories(sound PUBLIC ${CMAKE_SOURCE_DIR}/includes/libsample)
target_include_directories(shape PUBLIC ${CMAKE_SOURCE_DIR}/includes/libsample)
target_include_directories(sound PUBLIC ${CMAKE_SOURCE_DIR}/includes/libsample)

# library path
# target_link_directories(shape PUBLIC ${CMAKE_SOURCE_DIR}/build/lib/${CMAKE_BUILD_TYPE})
# target_link_directories(shape PUBLIC ${CMAKE_SOURCE_DIR}/build/_deps/fmt-build/${CMAKE_BUILD_TYPE})
# link_directories(${CMAKE_SOURCE_DIR}/build/lib/${CMAKE_BUILD_TYPE})
# link_directories(${CMAKE_SOURCE_DIR}/build/_deps/fmt-build/${CMAKE_BUILD_TYPE})
