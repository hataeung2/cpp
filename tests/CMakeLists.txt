project(
  tests
  VERSION 0.1
  DESCRIPTION "cpp sample tests"
  LANGUAGES CXX
)

include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/dependencies/googletest
  )
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)


set(SOURCES
  test_double_dispatch.cpp
)
add_executable(${PROJECT_NAME} ${SOURCES})

# includes, definitions, options
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_BINARY_DIR}/dependencies/googletest/googletest/include)
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_BINARY_DIR}/dependencies/googletest/googletest/include/gtest)
# target_include_directories(${PROJECT_NAME} PUBLIC ${CMAKE_SOURCE_DIR}/includes/...)
target_include_directories(${PROJECT_NAME} PUBLIC ${CMAKE_SOURCE_DIR}/modules)
target_include_directories(${PROJECT_NAME} PUBLIC ${CMAKE_SOURCE_DIR}/sample)

# to link
set(LIBS

)
# link targets, gtest to project
target_link_libraries(${PROJECT_NAME} PUBLIC
  ${LIBS} gtest gtest_main gmock 
)
