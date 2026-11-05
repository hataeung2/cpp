# Tests
project(atugcc_tests)

include(${atugcc_SOURCE_DIR}/cmake/atugcc_googletest.cmake)

set(TEST_SOURCES
  ../tests/testmain.cpp
  ../tests/test_double_dispatch.cpp
  ../tests/core/test_ring_buffer.cpp
  ../tests/core/test_logger.cpp
  ../tests/core/test_log_buffers.cpp
  ../tests/core/test_log_map.cpp
  ../tests/core/test_error_expected.cpp
  ../tests/core/test_dump_handle.cpp
  ../tests/core/test_posix_dump.cpp
  ../tests/core/test_timestamp.cpp
  ../tests/modules/test_core_module.cpp
  ../tests/modules/test_core_module_mixed.cpp
  ../tests/pattern/test_visualizer.cpp
  ../tests/pattern/test_diagram_split.cpp
  ../tests/pattern/test_event_stream.cpp
  ../tests/pattern/test_span_timing.cpp
  ../tests/scenario/test_scenario_step.cpp
)

add_executable(atugcc_tests ${TEST_SOURCES})

target_link_libraries(atugcc_tests PRIVATE
  atugcc_headers
  atugcc_core
  gtest
  gtest_main
  gmock
)
# Sanitizer builds, told by the build instead of compiler macros: Clang has no __SANITIZE_*__
# (only __has_feature), GCC and MSVC do (spec 070-13).
if(ATUGCC_SANITIZERS)
  target_compile_definitions(atugcc_tests PRIVATE ATUGCC_SANITIZED_BUILD)
endif()
# Scenario::workDir() root (tests/scenario/scenario.hpp; ScenarioStepTest uses it too)
set(ATUGCC_SCENARIO_WORK_ROOT ${CMAKE_CURRENT_BINARY_DIR}/scenario_work)
target_compile_definitions(atugcc_tests PRIVATE ATUGCC_SCENARIO_WORK_ROOT="${ATUGCC_SCENARIO_WORK_ROOT}")

# Test kinds (spec 040-02): every test registered here has exactly one of the labels
# unit (AllTests and the step-helper self-checks), scenario (atugcc_scenarios) and probe (a probe
# program, mostly driven by a script). Lessons label their own tests (lesson, long).
# ATUGCC_TEST_LAUNCHER (root CMakeLists.txt): setarch -R under TSan, empty otherwise.
set(ATUGCC_TSAN_ENVIRONMENT "")
if(ATUGCC_SANITIZERS MATCHES "thread")
  # deliberate racy crash-dump snapshot reads only (tests/tsan.supp)
  set(ATUGCC_TSAN_ENVIRONMENT "TSAN_OPTIONS=suppressions=${CMAKE_CURRENT_SOURCE_DIR}/tsan.supp")
endif()
add_test(NAME AllTests COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:atugcc_tests>)
set_tests_properties(AllTests PROPERTIES LABELS "unit")
if(ATUGCC_TSAN_ENVIRONMENT)
  set_tests_properties(AllTests PROPERTIES ENVIRONMENT "${ATUGCC_TSAN_ENVIRONMENT}")
endif()
# Step helper self-checks (spec 040-02 AC-3 b, c): inside gtest-spi's EXPECT_*_FAILURE the failure
# goes to a fake reporter, so HasFatalFailure() / HasFailure() cannot see it. These deliberately
# failing tests run in their own process and the output is checked here (the exit code is ignored
# when PASS_REGULAR_EXPRESSION is set). GTEST_OUTPUT is unset so the planned failures do not reach a
# build.py --report. Label unit: they test test code, not a user flow.
function(atugcc_step_self_run name case pass fail)
  add_test(NAME ${name}
    COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:atugcc_tests> --gtest_also_run_disabled_tests
            --gtest_filter=ScenarioStepSelfRun.${case})
  set_tests_properties(${name} PROPERTIES LABELS "unit"
    ENVIRONMENT_MODIFICATION "GTEST_OUTPUT=unset:"
    PASS_REGULAR_EXPRESSION "${pass}" FAIL_REGULAR_EXPRESSION "${fail}")
  if(ATUGCC_TSAN_ENVIRONMENT)
    set_tests_properties(${name} PROPERTIES ENVIRONMENT "${ATUGCC_TSAN_ENVIRONMENT}")
  endif()
endfunction()
atugcc_step_self_run(ScenarioStepFatalStops DISABLED_FatalStopsLaterSteps
  "step 1: first.*\\[skip 2\\] second.*returns=false,false" "BODY2_RAN")
atugcc_step_self_run(ScenarioStepFatalBefore DISABLED_FatalBeforeFirstStep
  "\\[skip 1\\] first" "BODY1_RAN")
atugcc_step_self_run(ScenarioStepNonFatalContinues DISABLED_NonFatalDoesNotStopLaterSteps
  "step 1: first.*\\[step 2\\] second.*BODY2_RAN.*returns=true,true" "\\[skip")

# Scenario tests (spec 040-02): a separate program so scenarios share no process-wide state with
# the unit tests (configureLogBuffers, ATUGCC_TRACE_OUT, the crash dump target are set once per
# process), and one CTest test and one process per scenario: scenario.<Suite>.<Name>, label scenario.
# Discovery runs the program after each build (POST_BUILD); TEST_LAUNCHER is used for discovery and
# for the runs. Add a scenario: a tests/scenario/scenario_<flow>.cpp file and a line below.
include(GoogleTest)
add_executable(atugcc_scenarios
  ../tests/scenario/scenario_traced_state_machine.cpp
  ../tests/scenario/scenario_logged_error_flow.cpp
)
target_link_libraries(atugcc_scenarios PRIVATE atugcc_headers atugcc_core gtest gtest_main)
target_compile_definitions(atugcc_scenarios PRIVATE ATUGCC_SCENARIO_WORK_ROOT="${ATUGCC_SCENARIO_WORK_ROOT}")
if(ATUGCC_SANITIZERS)
  target_compile_definitions(atugcc_scenarios PRIVATE ATUGCC_SANITIZED_BUILD)
endif()
if(ATUGCC_TEST_LAUNCHER)
  set_target_properties(atugcc_scenarios PROPERTIES TEST_LAUNCHER "${ATUGCC_TEST_LAUNCHER}")
endif()
set(ATUGCC_SCENARIO_PROPERTIES LABELS scenario TIMEOUT 120)
if(ATUGCC_TSAN_ENVIRONMENT)
  list(APPEND ATUGCC_SCENARIO_PROPERTIES ENVIRONMENT "${ATUGCC_TSAN_ENVIRONMENT}")
endif()
gtest_discover_tests(atugcc_scenarios
  TEST_PREFIX "scenario."
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
  DISCOVERY_TIMEOUT 30
  PROPERTIES ${ATUGCC_SCENARIO_PROPERTIES})

# Event stream end to end (spec 020-05): the probe writes ATUGCC_TRACE_OUT, the script checks it.
add_executable(trace_stream_probe ../tests/pattern/trace_stream_probe.cpp)
target_link_libraries(trace_stream_probe PRIVATE atugcc_headers)
find_package(Python3 3.8 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
  add_test(NAME TraceStream
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/pattern/check_trace_stream.py
            -- ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:trace_stream_probe>)
  set_tests_properties(TraceStream PROPERTIES LABELS "probe")
else()
  message(WARNING "Python 3.8+ not found: the TraceStream test (spec 020-05 AC-4, AC-5) is not registered")
endif()
# Span cost and flush interval (spec 020-06 AC-5, AC-6, AC-8): prints ns per span and checks that every
# line reaches the file with and without a flush interval (and, in Release, that the interval is faster).
# Small counts keep Debug and sanitizer suites short; the full run (no arguments) is a Release measurement.
add_executable(span_cost_probe ../tests/pattern/span_cost_probe.cpp)
target_link_libraries(span_cost_probe PRIVATE atugcc_headers)
add_test(NAME SpanCost COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:span_cost_probe> 20000 20000)
set_tests_properties(SpanCost PROPERTIES TIMEOUT 300 LABELS "probe")
# Crash dump preparation (spec 010-08 AC-5, AC-6, AC-7): the dump target is process-wide, so each
# check runs in a fresh process. cleanup exits normally; check-removed then finds no empty dump file.
add_executable(dump_prepare_probe ../tests/core/dump_prepare_probe.cpp)
target_link_libraries(dump_prepare_probe PRIVATE atugcc_headers atugcc_core)
set(ATUGCC_DUMP_PREPARE_DIR ${CMAKE_CURRENT_BINARY_DIR}/dump_prepare)
foreach(mode off once replace cleanup)
  add_test(NAME DumpPrepare_${mode}
    COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:dump_prepare_probe> ${mode} ${ATUGCC_DUMP_PREPARE_DIR}/${mode})
  set_tests_properties(DumpPrepare_${mode} PROPERTIES LABELS "probe")
endforeach()
add_test(NAME DumpPrepare_check-removed
  COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:dump_prepare_probe> check-removed ${ATUGCC_DUMP_PREPARE_DIR}/cleanup)
set_tests_properties(DumpPrepare_cleanup PROPERTIES FIXTURES_SETUP dump_prepare_cleanup)
set_tests_properties(DumpPrepare_check-removed PROPERTIES FIXTURES_REQUIRED dump_prepare_cleanup LABELS "probe")
# ATUGCC_LOG_SLOTS sets the default per-thread buffer size (spec 010-09 AC-6b)
add_test(NAME LogSlotsFromEnvironment
  COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:dump_prepare_probe> slots ${ATUGCC_DUMP_PREPARE_DIR}/slots)
set_tests_properties(LogSlotsFromEnvironment PROPERTIES ENVIRONMENT "ATUGCC_LOG_SLOTS=128" PASS_REGULAR_EXPRESSION "slots=128" LABELS "probe")
# Shared Logger vs Logger per thread vs DbgBuf only (spec 010-08 AC-10): small counts here; the
# measurement (no arguments) runs on a Release preset and goes into the testrecord.
add_executable(logger_contention_probe ../tests/core/logger_contention_probe.cpp)
target_link_libraries(logger_contention_probe PRIVATE atugcc_headers atugcc_core)
add_test(NAME LoggerContention COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:logger_contention_probe> 2000 1)
set_tests_properties(LoggerContention PROPERTIES TIMEOUT 300 LABELS "probe")
# Log preservation per way of ending (spec 010-09 AC-2 ... AC-5, AC-10) and delivery order across a
# thread handoff (spec 010-09-01, mode handoff): crash_probe logs from
# several threads and ends normally, crashes, or waits to be killed; the script reads the files and
# the dump. Sanitizer runtimes own the crash signals, so sanitizer presets run the non-crash modes only.
add_executable(crash_probe ../tests/core/crash_probe.cpp)
target_link_libraries(crash_probe PRIVATE atugcc_headers atugcc_core)
if(Python3_Interpreter_FOUND)
  if(ATUGCC_SANITIZERS)
    set(ATUGCC_CRASH_MODES normal,exit,quickexit,killme,handoff)
    set(ATUGCC_CRASH_LINES 20000)
  else()
    set(ATUGCC_CRASH_MODES normal,exit,quickexit,segv,abort,terminate,stackoverflow,killme,handoff)
    set(ATUGCC_CRASH_LINES 100000)
  endif()
  add_test(NAME CrashDump
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/core/check_crash_dump.py
            --probe $<TARGET_FILE:crash_probe> --work ${CMAKE_CURRENT_BINARY_DIR}/crash_probe
            --modes ${ATUGCC_CRASH_MODES} --lines ${ATUGCC_CRASH_LINES} -- ${ATUGCC_TEST_LAUNCHER})
  set_tests_properties(CrashDump PROPERTIES TIMEOUT 600 LABELS "probe")
endif()
# Memory-mapped log buffer probe and recovery (spec 010-10, plan D5)
add_executable(log_map_probe ../tests/core/log_map_probe.cpp)
target_link_libraries(log_map_probe PRIVATE atugcc_headers atugcc_core)
if(Python3_Interpreter_FOUND)
  if(ATUGCC_SANITIZERS)
    set(ATUGCC_LOG_MAP_EXTRA --no-crash)
  else()
    set(ATUGCC_LOG_MAP_EXTRA)
  endif()
  add_test(NAME LogMap
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/core/check_log_map.py
            --probe $<TARGET_FILE:log_map_probe> --work ${CMAKE_CURRENT_BINARY_DIR}/log_map_probe
            ${ATUGCC_LOG_MAP_EXTRA} -- ${ATUGCC_TEST_LAUNCHER})
  set_tests_properties(LogMap PROPERTIES TIMEOUT 600 LABELS "probe")
endif()
# Web playground runner (spec 070-02 AC-5, AC-11, AC-12): a fixture program plays slow or
# misbehaving lessons; test_server.py drives it through the runner and the HTTP server.
add_executable(playground_fixture ../tests/playground/playground_fixture.cpp)
target_link_libraries(playground_fixture PRIVATE atugcc_headers)
if(ATUGCC_SANITIZERS)
  target_compile_definitions(playground_fixture PRIVATE ATUGCC_SANITIZED_BUILD)
endif()
if(UNIX AND Python3_Interpreter_FOUND AND Python3_VERSION VERSION_GREATER_EQUAL 3.11)
  add_test(NAME PlaygroundServer
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/web/server/test_server.py
            --fixture $<TARGET_FILE:playground_fixture> -- ${ATUGCC_TEST_LAUNCHER})
  set_tests_properties(PlaygroundServer PROPERTIES TIMEOUT 420 LABELS "probe;playground")
elseif(UNIX)
  message(WARNING "Python 3.11+ not found: the PlaygroundServer test (spec 070-02) is not registered")
endif()
if(UNIX)
  # split debug symbols for test binary too
  if(COMMAND add_debug_symbol_split)
    add_debug_symbol_split(atugcc_tests)
  endif()
endif()

# Lesson console UTF-8 code page switching and restoration (spec 090-06 AC-8, AC-9).
# Note: lessons/ is added after tests/ in the root CMakeLists.txt, so if(TARGET ...) cannot
# be used here, but link targets and $<TARGET_FILE:...> generator expressions resolve at generate time.
if(WIN32 AND ATUGCC_BUILD_LESSONS AND Python3_Interpreter_FOUND AND Python3_VERSION VERSION_GREATER_EQUAL 3.10)
  add_executable(console_cp_probe ../tests/console/console_cp_probe.cpp)
  target_link_libraries(console_cp_probe PRIVATE atugcc_headers atugcc_lesson_console)
  add_test(NAME LessonConsoleCodePage
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/console/check_console_cp.py
            --probe $<TARGET_FILE:console_cp_probe> --lesson $<TARGET_FILE:lesson_device_state_machine>)
  set_tests_properties(LessonConsoleCodePage PROPERTIES TIMEOUT 240 LABELS "probe")
elseif(WIN32 AND ATUGCC_BUILD_LESSONS)
  message(WARNING "Python 3.10+ not found: the LessonConsoleCodePage test (spec 090-06 AC-8, AC-9) is not registered")
endif()

