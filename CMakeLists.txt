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
  set(CMAKE_GENERATOR_PLATFORM "x64")
  set(CMAKE_VS_PLATFORM_TOOLSET_HOST_ARCHITECTURE "x64")
  set(TARGET_ARCH ${CMAKE_VS_PLATFORM_TOOLSET_HOST_ARCHITECTURE}) 
  message(STATUS "GENERATOR TOOLSET: ${CMAKE_GENERATOR_TOOLSET}")
  message(STATUS "HOST_ARCHITECTURE: ${CMAKE_VS_PLATFORM_TOOLSET_HOST_ARCHITECTURE}")
    
  
  set(CMAKE_CXX_FLAGS "/W3 /EHsc /wd4109") # /WX -> all warings are errors
  string(REGEX REPLACE "/W[1-4]" "/W1" CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
  set(CMAKE_CXX_FLAGS_DEBUG "/ZI") # /ZI	Includes debug information in a program database compatible with Edit and Continue. (x64 only)
  set(CMAKE_CXX_FLAGS_RELEASE "/O2") # /O2	Creates fast code.
  set(CMAKE_CXX_FLAGS_MINSIZEREL "/Os") # /Os	Favors small code.
  set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "/O2 /Zi") # /Zi	Generates complete debugging information.
  elseif (${CMAKE_SYSTEM_NAME} MATCHES "Linux" OR ${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
  set(CMAKE_CXX_FLAGS "-O1 -Wall")
  set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g")
  set(CMAKE_CXX_FLAGS_RELEASE "-O2")
  set(CMAKE_CXX_FLAGS_MINSIZEREL "-Os")
  set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-Og -g")

endif ()
# output dir for library, binary - synced with Visual Studio
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${OUTPUT_DIR}/${CMAKE_SYSTEM_NAME}/${TARGET_ARCH}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${OUTPUT_DIR}/${CMAKE_SYSTEM_NAME}/${TARGET_ARCH}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${OUTPUT_DIR}/${CMAKE_SYSTEM_NAME}/${TARGET_ARCH}/bin)



# source files
if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
  # library packages
  set(PKG_CONFIG_EXECUTABLE "C:/msys64/usr/bin/pkg-config.exe")
  # PostgreSQL first should be installed then set the path below
  set(PostgreSQL_LIBRARY "C:/Program Files/PostgreSQL/17/lib/libpq.lib")
  set(PostgreSQL_INCLUDE_DIR "C:/Program Files/PostgreSQL/17/include")
  set(PostgreSQL_BINARY_DIR "C:/Program Files/PostgreSQL/17/bin")

  # SOURCE
  set(SOURCE
    modules/sample_module.cppm
    modules/log/ring_buffer.cpp
    modules/log/alog.cppm
    main.cpp
  )  
elseif (${CMAKE_SYSTEM_NAME} MATCHES "Linux" OR ${CMAKE_SYSTEM_NAME} MATCHES "Darwin")

  # SOURCE
  set(SOURCE
    modules/log/ring_buffer.cpp
    main.cpp
  )  

endif ()
# library packages
include(FetchContent)
FetchContent_Declare(
  pqxx
  URL https://github.com/jtv/libpqxx/archive/refs/tags/7.9.2.zip
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/dependencies/pqxx
  )
FetchContent_MakeAvailable(pqxx)
find_package(PostgreSQL REQUIRED)


set (APP cpp_sample)

add_executable(${APP} ${SOURCE})

target_include_directories(${APP} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/modules)
target_include_directories(${APP} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/modules/log)
target_include_directories(${APP} PUBLIC ${CMAKE_SOURCE_DIR}/includes/libsample)
target_include_directories(${APP} PUBLIC ${CMAKE_SOURCE_DIR}/dependencies/pqxx/include)

if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
  set(PSQL_DLL_1 ${PostgreSQL_BINARY_DIR}/libpq.dll)
  set(PSQL_DLL_2 ${PostgreSQL_BINARY_DIR}/libintl-9.dll)
  set(PSQL_DLL_3 ${PostgreSQL_BINARY_DIR}/libssl-3-x64.dll)
  set(PSQL_DLL_4 ${PostgreSQL_BINARY_DIR}/libcrypto-3-x64.dll)
  set(PSQL_DLL_5 ${PostgreSQL_BINARY_DIR}/libwinpthread-1.dll)
  set(PSQL_DLL_6 ${PostgreSQL_BINARY_DIR}/libiconv-2.dll)
  add_custom_command(TARGET ${APP} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${PSQL_DLL_1}" $<TARGET_FILE_DIR:${APP}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${PSQL_DLL_2}" $<TARGET_FILE_DIR:${APP}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${PSQL_DLL_3}" $<TARGET_FILE_DIR:${APP}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${PSQL_DLL_4}" $<TARGET_FILE_DIR:${APP}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${PSQL_DLL_5}" $<TARGET_FILE_DIR:${APP}>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${PSQL_DLL_6}" $<TARGET_FILE_DIR:${APP}>
  )
  target_link_libraries(${APP} pqxx shape sound)
elseif (${CMAKE_SYSTEM_NAME} MATCHES "Linux" OR ${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
  target_link_libraries(${APP} pqxx fmt shape sound)
endif ()



# libraries
add_subdirectory(libs)

# tests
add_subdirectory(tests)