# Lessons (spec 070-01)
# Every lessons/tracks/<track>/<lesson>/lesson.toml becomes an executable lesson_<id>
# (bin/lessons/) and, with ATUGCC_BUILD_TESTS, a smoke test lesson.<id> (exit code 0 within
# the time limit). A new lesson folder is picked up at the next build (CONFIGURE_DEPENDS).
#
# CMake cannot parse TOML: it reads id, sources, profile and timeout with line regexes, so those
# keys are written on one line. tools/lessons.py check validates the full schema and reads each
# manifest with these same regexes, reporting any difference from the TOML values.

file(GLOB _atugcc_lesson_manifests CONFIGURE_DEPENDS
  "${CMAKE_CURRENT_SOURCE_DIR}/tracks/*/*/lesson.toml")

foreach(_manifest IN LISTS _atugcc_lesson_manifests)
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
  foreach(_q IN LISTS _quoted)
    string(REPLACE "\"" "" _name "${_q}")
    list(APPEND _sources "${_dir}/${_name}")
  endforeach()
  if(NOT _sources)
    message(FATAL_ERROR "${_manifest}: sources is empty ${_hint}")
  endif()

  set(_profile "quick")
  if(_text MATCHES "(^|\n)profile[ \t]*=[ \t]*\"(quick|long)\"")
    set(_profile "${CMAKE_MATCH_2}")
  endif()
  set(_timeout 300)
  if(_text MATCHES "(^|\n)timeout[ \t]*=[ \t]*([0-9]+)")
    set(_timeout "${CMAKE_MATCH_2}")
  endif()

  add_executable(lesson_${_id} ${_sources})
  target_include_directories(lesson_${_id} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
  target_link_libraries(lesson_${_id} PRIVATE atugcc_core)
  set_target_properties(lesson_${_id} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/lessons")

  if(ATUGCC_BUILD_TESTS)
    add_test(NAME lesson.${_id} COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:lesson_${_id}>)
    if(_profile STREQUAL "long")
      set_tests_properties(lesson.${_id} PROPERTIES TIMEOUT ${_timeout} LABELS "lesson;long")
    else()
      set_tests_properties(lesson.${_id} PROPERTIES TIMEOUT 10 LABELS "lesson")
    endif()
  endif()
endforeach()
