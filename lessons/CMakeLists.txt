# Lessons (spec 070-01)
# Every lessons/tracks/<track>/<lesson>/lesson.toml becomes an executable lesson_<id>
# (bin/lessons/) and, with ATUGCC_BUILD_TESTS, a smoke test lesson.<id> (exit code 0 within
# the time limit). A new lesson folder is picked up at the next build (CONFIGURE_DEPENDS).
#
# CMake cannot parse TOML: it reads id, sources, profile, timeout and gtest with line regexes, so
# those keys are written on one line. tools/lessons.py check validates the full schema and reads
# each manifest with these same regexes, reporting any difference from the TOML values.
# Sources ending in .cppm are module interface or partition units (spec 070-14); the rest,
# implementation units included, are ordinary sources. The first source is a .cpp entry point.
# gtest = true (spec 070-15) links GoogleTest (cmake/atugcc_googletest.cmake, also used by tests/)
# and gives the lesson the scenario step helper: include path tests/scenario ("scenario.hpp") and
# ATUGCC_SCENARIO_WORK_ROOT under this build directory.
#
# Practice copies (spec 070-16): practice/lessons/tracks/<track>/<lesson>/ (git-ignored, made by
# tools/practice.py or the web page) become practice_<id> (bin/practice/) from the same rules. Their
# include path puts practice/lessons before lessons/, so a practice copy of a unit header wins.
# Practice targets are EXCLUDE_FROM_ALL and have no smoke test: a half-done exercise breaks neither
# the full build nor ctest. A new copy is picked up at the next build (CONFIGURE_DEPENDS).
#
# Exercises (spec 070-17): a lesson with exercises.toml also gets lesson.<id>.exercises_verify,
# which runs the built original through tools/exercises.py verify: the unchanged program must pass
# none of the automatic exercises (an `expect` line the original already prints is a mistake).

# spec 090-06; an OBJECT library so the linker keeps the static object although nothing references it
add_library(atugcc_lesson_console OBJECT support/console_utf8.cpp)
target_link_libraries(atugcc_lesson_console PRIVATE atugcc_headers)

set(_atugcc_practice_lessons "${atugcc_SOURCE_DIR}/practice/lessons")
file(GLOB _atugcc_lesson_manifests CONFIGURE_DEPENDS
  "${CMAKE_CURRENT_SOURCE_DIR}/tracks/*/*/lesson.toml")
file(GLOB _atugcc_practice_manifests CONFIGURE_DEPENDS
  "${_atugcc_practice_lessons}/tracks/*/*/lesson.toml")
# exercise definitions (spec 070-17): a new exercises.toml registers its verify test at the next build
file(GLOB _atugcc_exercise_files CONFIGURE_DEPENDS
  "${CMAKE_CURRENT_SOURCE_DIR}/tracks/*/*/exercises.toml")
set(_atugcc_exercise_python OFF)
if(ATUGCC_BUILD_TESTS AND _atugcc_exercise_files)
  # the same request as tests/CMakeLists.txt (the cached interpreter is reused), then the version
  # tools/exercises.py needs (tomllib)
  find_package(Python3 3.8 COMPONENTS Interpreter)
  if(Python3_Interpreter_FOUND AND Python3_VERSION VERSION_GREATER_EQUAL 3.11)
    set(_atugcc_exercise_python ON)
  else()
    message(WARNING "Python 3.11+ not found: the lesson.<id>.exercises_verify tests (spec 070-17) are not registered")
  endif()
endif()

foreach(_manifest IN LISTS _atugcc_lesson_manifests _atugcc_practice_manifests)
  # kind of target: the original lesson, or its practice copy (spec 070-16)
  if(_manifest IN_LIST _atugcc_practice_manifests)
    set(_kind "practice")
    set(_bin "practice")
    set(_includes "${_atugcc_practice_lessons}" "${CMAKE_CURRENT_SOURCE_DIR}")
    set(_work "practice_scenario_work")
  else()
    set(_kind "lesson")
    set(_bin "lessons")
    set(_includes "${CMAKE_CURRENT_SOURCE_DIR}")
    set(_work "scenario_work")
  endif()
  get_filename_component(_dir "${_manifest}" DIRECTORY)
  # editing id/sources/profile/timeout in an existing manifest reconfigures too
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_manifest}")
  file(READ "${_manifest}" _text)
  set(_hint "(run: py -3 tools/lessons.py check)")

  if(NOT _text MATCHES "(^|\n)id[ \t]*=[ \t]*\"([a-z0-9_]+)\"")
    message(FATAL_ERROR "${_manifest}: no valid id ${_hint}")
  endif()
  set(_id "${CMAKE_MATCH_2}")

  if(NOT _text MATCHES "(^|\n)sources[ \t]*=[ \t]*\\[([^]\n]*)\\]")
    message(FATAL_ERROR "${_manifest}: no one-line sources = [...] ${_hint}")
  endif()
  string(REGEX MATCHALL "\"[^\"]+\"" _quoted "${CMAKE_MATCH_2}")
  set(_sources "")
  set(_module_sources "")
  foreach(_q IN LISTS _quoted)
    string(REPLACE "\"" "" _name "${_q}")
    # spec 070-14: module interface and partition units (.cppm) go into a CXX_MODULES file set
    if(_name MATCHES "\\.cppm$")
      list(APPEND _module_sources "${_dir}/${_name}")
    else()
      list(APPEND _sources "${_dir}/${_name}")
    endif()
  endforeach()
  if(NOT _sources)
    message(FATAL_ERROR "${_manifest}: sources has no non-module (.cpp) file ${_hint}")
  endif()

  set(_profile "quick")
  if(_text MATCHES "(^|\n)profile[ \t]*=[ \t]*\"(quick|long)\"")
    set(_profile "${CMAKE_MATCH_2}")
  endif()
  set(_timeout 300)
  if(_text MATCHES "(^|\n)timeout[ \t]*=[ \t]*([0-9]+)")
    set(_timeout "${CMAKE_MATCH_2}")
  endif()

  set(_target "${_kind}_${_id}")
  if(_kind STREQUAL "practice")
    add_executable(${_target} EXCLUDE_FROM_ALL ${_sources})
  else()
    add_executable(${_target} ${_sources})
  endif()
  if(_module_sources)
    target_sources(${_target} PRIVATE FILE_SET CXX_MODULES BASE_DIRS "${_dir}" FILES ${_module_sources})
  endif()
  target_include_directories(${_target} PRIVATE ${_includes})
  target_link_libraries(${_target} PRIVATE atugcc_core atugcc_lesson_console)
  if(_text MATCHES "(^|\n)gtest[ \t]*=[ \t]*true")
    include(${atugcc_SOURCE_DIR}/cmake/atugcc_googletest.cmake)
    target_link_libraries(${_target} PRIVATE gtest)
    target_include_directories(${_target} PRIVATE "${atugcc_SOURCE_DIR}/tests/scenario")
    target_compile_definitions(${_target} PRIVATE
      ATUGCC_SCENARIO_WORK_ROOT="${CMAKE_CURRENT_BINARY_DIR}/${_work}")
    if(ATUGCC_SANITIZERS)
      target_compile_definitions(${_target} PRIVATE ATUGCC_SANITIZED_BUILD)
    endif()
  endif()
  set_target_properties(${_target} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/${_bin}")

  if(ATUGCC_BUILD_TESTS AND _kind STREQUAL "lesson")
    add_test(NAME lesson.${_id} COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:lesson_${_id}>)
    if(_profile STREQUAL "long")
      set_tests_properties(lesson.${_id} PROPERTIES TIMEOUT ${_timeout} LABELS "lesson;long")
    else()
      set_tests_properties(lesson.${_id} PROPERTIES TIMEOUT 10 LABELS "lesson")
    endif()
    # spec 070-17: the unchanged program must pass none of the lesson's automatic exercises
    if(_atugcc_exercise_python AND "${_dir}/exercises.toml" IN_LIST _atugcc_exercise_files)
      add_test(NAME lesson.${_id}.exercises_verify
        COMMAND ${Python3_EXECUTABLE} ${atugcc_SOURCE_DIR}/tools/exercises.py verify ${_id}
                --exe ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:lesson_${_id}>)
      get_test_property(lesson.${_id} TIMEOUT _verify_timeout)
      get_test_property(lesson.${_id} LABELS _verify_labels)
      set_tests_properties(lesson.${_id}.exercises_verify PROPERTIES
        TIMEOUT ${_verify_timeout} LABELS "${_verify_labels}")
    endif()
  endif()
endforeach()
