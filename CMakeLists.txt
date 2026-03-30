cmake_minimum_required(VERSION 3.26)

project(
  atugcc
  VERSION 0.1.0
  DESCRIPTION "C++23 framework library"
  LANGUAGES CXX
)

# Options
option(ATUGCC_ENABLE_PQXX "Enable PostgreSQL support" OFF)
option(ATUGCC_BUILD_TESTS "Build tests" ON)
option(ATUGCC_BUILD_SAMPLES "Build samples" ON)

if (CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(CMAKE_CXX_SCAN_FOR_MODULES ON)
endif()

# Platform specific settings / Output directories
if (CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
  set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
else()
  set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
  set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
endif()

# Boost (header-only lockfree queue)
# Configure with: cmake -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ...
find_package(Boost CONFIG REQUIRED)

# Core library (Headers)
add_library(atugcc_headers INTERFACE)
target_include_directories(atugcc_headers INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
# 이 부분을 추가하세요!
target_link_libraries(atugcc_headers INTERFACE Boost::boost) 
target_compile_features(atugcc_headers INTERFACE cxx_std_23)

if (CMAKE_SYSTEM_NAME MATCHES "Windows")
  target_compile_options(atugcc_headers INTERFACE /W4 /EHsc /wd4109)
else()
  target_compile_options(atugcc_headers INTERFACE -Wall -Wextra)
endif()

# Core framework (Sources)
set(CORE_SOURCES
  src/core/ring_buffer.cpp
  src/core/log_queue.cpp
  src/core/timestamp.cpp
)
add_library(atugcc_core STATIC ${CORE_SOURCES})
target_link_libraries(atugcc_core PUBLIC atugcc_headers)

if (CMAKE_SYSTEM_NAME MATCHES "Windows")
  # C++20 modules (supported primarily on MSVC currently)
  target_sources(atugcc_core
    PUBLIC
    FILE_SET CXX_MODULES
    FILES
      src/core/alog.cppm
      modules/sample_module.cppm
  )
endif()

# Dependencies: PQXX (Optional)
if (ATUGCC_ENABLE_PQXX)
  include(FetchContent)
  FetchContent_Declare(
    pqxx
    URL https://github.com/jtv/libpqxx/archive/refs/tags/7.9.2.zip
  )
  FetchContent_MakeAvailable(pqxx)
  if (CMAKE_SYSTEM_NAME MATCHES "Windows")
    set(PostgreSQL_INCLUDE_DIR "C:/Program Files/PostgreSQL/17/include")
    target_include_directories(pqxx PUBLIC ${PostgreSQL_INCLUDE_DIR})
  endif()
endif()

# Libraries
add_subdirectory(libs)

# Samples
if (ATUGCC_BUILD_SAMPLES)
  set(SAMPLE_SOURCES
    main.cpp
  )
  add_executable(atugcc_sample ${SAMPLE_SOURCES})
  target_link_libraries(atugcc_sample PRIVATE atugcc_core shape sound)
  if (ATUGCC_ENABLE_PQXX)
    target_link_libraries(atugcc_sample PRIVATE pqxx)
    target_compile_definitions(atugcc_sample PRIVATE ATUGCC_ENABLE_PQXX)
  endif()
endif()

# Tests
if (ATUGCC_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()