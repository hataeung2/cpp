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
  ../tests/pattern/test_diagram_split.cpp
  ../tests/pattern/test_event_stream.cpp
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

# Event stream end to end (spec 020-05): the probe writes ATUGCC_TRACE_OUT, the script checks it.
add_executable(trace_stream_probe ../tests/pattern/trace_stream_probe.cpp)
target_link_libraries(trace_stream_probe PRIVATE atugcc_headers)
find_package(Python3 3.8 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME TraceStream
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/pattern/check_trace_stream.py
            -- ${_atugcc_test_launcher} $<TARGET_FILE:trace_stream_probe>)
else()
  message(WARNING "Python 3.8+ not found: the TraceStream test (spec 020-05 AC-4, AC-5) is not registered")
endif()
if(UNIX)
  # split debug symbols for test binary too
  if(COMMAND add_debug_symbol_split)
    add_debug_symbol_split(atugcc_tests)
  endif()
endif()
