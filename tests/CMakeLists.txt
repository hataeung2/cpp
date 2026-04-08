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
  ../tests/core/test_error_expected.cpp
  ../tests/core/test_dump_handle.cpp
  ../tests/core/test_posix_dump.cpp
  ../tests/core/test_timestamp.cpp
)

add_executable(atugcc_tests ${TEST_SOURCES})

target_link_libraries(atugcc_tests PRIVATE
  atugcc_headers
  atugcc_core
  gtest
  gtest_main
  gmock
)

add_test(NAME AllTests COMMAND atugcc_tests)
if(UNIX)
  # split debug symbols for test binary too
  if(COMMAND add_debug_symbol_split)
    add_debug_symbol_split(atugcc_tests)
  endif()
endif()
