cmake_minimum_required(VERSION 3.26)

project(
  cpp20samplecode
  VERSION 0.0.0.1
  DESCRIPTION "C++20 sample code"
  LANGUAGES CXX
)

# compiler c++ standard set
set(CMAKE_CXX_STANDARD 20 CACHE STRING "C++ version selection")  # or 11, 14, 17, 20

# platform specific
message(STATUS "ENVIRONMENT OS: ${CMAKE_SYSTEM_NAME}")
if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
  message(STATUS "PLATFORM TOOLSET: ${CMAKE_VS_PLATFORM_TOOLSET}, SDKVER: ${CMAKE_VS_WINDOWS_TARGET_PLATFORM_VERSION}, TARGETVER: ${CMAKE_SYSTEM_VERSION}")
  # x86, x64, ...
  set(CMAKE_VS_PLATFORM_TOOLSET_HOST_ARCHITECTURE "x64")
  set(TARGET_ARCH ${CMAKE_VS_PLATFORM_TOOLSET_HOST_ARCHITECTURE}) 
  message(STATUS "GENERATOR TOOLSET: ${CMAKE_GENERATOR_TOOLSET}")
  message(STATUS "HOST_ARCHITECTURE: ${CMAKE_VS_PLATFORM_TOOLSET_HOST_ARCHITECTURE}")
    
  
  set(CMAKE_CXX_FLAGS "/W3 /EHsc /wd4109") # /WX -> all warings are errors
  string(REGEX REPLACE "/W[1-4]" "/W1" CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
  set(CMAKE_CXX_FLAGS_DEBUG "/ZI") # /ZI	Includes debug information in a program database compatible with Edit and Continue. (x86 only)
  set(CMAKE_CXX_FLAGS_RELEASE "/O2") # /O2	Creates fast code.
  set(CMAKE_CXX_FLAGS_MINSIZEREL "/Os") # /Os	Favors small code.
  set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "/O2 /Zi") # /Zi	Generates complete debugging information.
elseif (${CMAKE_SYSTEM_NAME} MATCHES "Linux" OR ${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
  set(CMAKE_CXX_FLAGS "-O1 -Wall")
  set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g")
  set(CMAKE_CXX_FLAGS_RELEASE "-O2")
  set(CMAKE_CXX_FLAGS_MINSIZEREL "-Os")
  set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-Og -g")
  set(CMAKE_CXX_FLAGS "-fmodules-ts")
endif ()
# output dir for library, binary - synced with Visual Studio
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${OUTPUT_DIR}/${CMAKE_SYSTEM_NAME}/${TARGET_ARCH}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${OUTPUT_DIR}/${CMAKE_SYSTEM_NAME}/${TARGET_ARCH}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${OUTPUT_DIR}/${CMAKE_SYSTEM_NAME}/${TARGET_ARCH}/bin)



# source files
if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
set(SOURCE
  modules/sample_module.cppm
  modules/ring_buffer.cpp
  modules/alog.cppm
  main.cpp
)  
elseif (${CMAKE_SYSTEM_NAME} MATCHES "Linux" OR ${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
set(SOURCE
  modules/ring_buffer.cpp
  main.cpp
)  
endif ()
set (APP cpp_sample)
add_executable(${APP} ${SOURCE})
target_include_directories(${APP} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/modules)

if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
  # 
elseif (${CMAKE_SYSTEM_NAME} MATCHES "Linux" OR ${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
  target_link_libraries(${APP} fmt)
endif ()

