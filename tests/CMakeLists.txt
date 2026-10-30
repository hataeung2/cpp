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
  ../tests/pattern/test_span_timing.cpp
)

add_executable(atugcc_tests ${TEST_SOURCES})

target_link_libraries(atugcc_tests PRIVATE
  atugcc_headers
  atugcc_core
  gtest
  gtest_main
  gmock
)

# ATUGCC_TEST_LAUNCHER (root CMakeLists.txt): setarch -R under TSan, empty otherwise.
add_test(NAME AllTests COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:atugcc_tests>)

# Event stream end to end (spec 020-05): the probe writes ATUGCC_TRACE_OUT, the script checks it.
add_executable(trace_stream_probe ../tests/pattern/trace_stream_probe.cpp)
target_link_libraries(trace_stream_probe PRIVATE atugcc_headers)
find_package(Python3 3.8 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME TraceStream
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/pattern/check_trace_stream.py
            -- ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:trace_stream_probe>)
else()
  message(WARNING "Python 3.8+ not found: the TraceStream test (spec 020-05 AC-4, AC-5) is not registered")
endif()
# Span cost and flush interval (spec 020-06 AC-5, AC-6, AC-8): prints ns per span and checks that every
# line reaches the file with and without a flush interval (and, in Release, that the interval is faster).
# Small counts keep Debug and sanitizer suites short; the full run (no arguments) is a Release measurement.
add_executable(span_cost_probe ../tests/pattern/span_cost_probe.cpp)
target_link_libraries(span_cost_probe PRIVATE atugcc_headers)
add_test(NAME SpanCost COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:span_cost_probe> 20000 20000)
set_tests_properties(SpanCost PROPERTIES TIMEOUT 300)
# Crash dump preparation (spec 010-08 AC-5, AC-6, AC-7): the dump target is process-wide, so each
# check runs in a fresh process. cleanup exits normally; check-removed then finds no empty dump file.
add_executable(dump_prepare_probe ../tests/core/dump_prepare_probe.cpp)
target_link_libraries(dump_prepare_probe PRIVATE atugcc_headers atugcc_core)
set(ATUGCC_DUMP_PREPARE_DIR ${CMAKE_CURRENT_BINARY_DIR}/dump_prepare)
foreach(mode off once replace cleanup)
  add_test(NAME DumpPrepare_${mode}
    COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:dump_prepare_probe> ${mode} ${ATUGCC_DUMP_PREPARE_DIR}/${mode})
endforeach()
add_test(NAME DumpPrepare_check-removed
  COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:dump_prepare_probe> check-removed ${ATUGCC_DUMP_PREPARE_DIR}/cleanup)
set_tests_properties(DumpPrepare_cleanup PROPERTIES FIXTURES_SETUP dump_prepare_cleanup)
set_tests_properties(DumpPrepare_check-removed PROPERTIES FIXTURES_REQUIRED dump_prepare_cleanup)
# Shared Logger vs Logger per thread vs DbgBuf only (spec 010-08 AC-10): small counts here; the
# measurement (no arguments) runs on a Release preset and goes into the testrecord.
add_executable(logger_contention_probe ../tests/core/logger_contention_probe.cpp)
target_link_libraries(logger_contention_probe PRIVATE atugcc_headers atugcc_core)
add_test(NAME LoggerContention COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:logger_contention_probe> 2000 1)
set_tests_properties(LoggerContention PROPERTIES TIMEOUT 300)
# Web playground runner (spec 070-02 AC-5, AC-11, AC-12): a fixture program plays slow or
# misbehaving lessons; test_server.py drives it through the runner and the HTTP server.
add_executable(playground_fixture ../tests/playground/playground_fixture.cpp)
target_link_libraries(playground_fixture PRIVATE atugcc_headers)
if(UNIX AND Python3_Interpreter_FOUND AND Python3_VERSION VERSION_GREATER_EQUAL 3.11)
  add_test(NAME PlaygroundServer
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/web/server/test_server.py
            --fixture $<TARGET_FILE:playground_fixture> -- ${ATUGCC_TEST_LAUNCHER})
  set_tests_properties(PlaygroundServer PROPERTIES TIMEOUT 420 LABELS "playground")
elseif(UNIX)
  message(WARNING "Python 3.11+ not found: the PlaygroundServer test (spec 070-02) is not registered")
endif()
if(UNIX)
  # split debug symbols for test binary too
  if(COMMAND add_debug_symbol_split)
    add_debug_symbol_split(atugcc_tests)
  endif()
endif()
