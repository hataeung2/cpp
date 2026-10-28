# Tests
project(atugcc_tests)

include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

set(TEST_SOURCES
  ../tests/testmain.cpp
  ../tests/test_double_dispatch.cpp
  ../tests/core/test_ring_buffer.cpp
  ../tests/core/test_logger.cpp
  ../tests/core/test_error_expected.cpp
  ../tests/core/test_dump_handle.cpp
  ../tests/core/test_posix_dump.cpp
  ../tests/core/test_timestamp.cpp
  ../tests/pattern/test_visualizer.cpp
)

add_executable(atugcc_tests ${TEST_SOURCES})

target_link_libraries(atugcc_tests PRIVATE
  atugcc_headers
  atugcc_core
  gtest
  gtest_main
  gmock
)

# ThreadSanitizer in GCC 13 aborts with "unexpected memory mapping" under the high ASLR
# entropy of current kernels (WSL2, Ubuntu 24.04): run the tests without ASLR.
set(_atugcc_test_launcher "")
if(UNIX AND "thread" IN_LIST ATUGCC_SANITIZERS)
  find_program(ATUGCC_SETARCH setarch)
  if(ATUGCC_SETARCH)
    set(_atugcc_test_launcher ${ATUGCC_SETARCH} ${CMAKE_HOST_SYSTEM_PROCESSOR} -R)
  endif()
endif()
add_test(NAME AllTests COMMAND ${_atugcc_test_launcher} $<TARGET_FILE:atugcc_tests>)
if(UNIX)
  # split debug symbols for test binary too
  if(COMMAND add_debug_symbol_split)
    add_debug_symbol_split(atugcc_tests)
  endif()
endif()
