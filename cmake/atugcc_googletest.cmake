# GoogleTest for tests/ and for lessons with `gtest = true` in lesson.toml (spec 070-15).
# Both include this file; the guard makes the second include a no-op, so one set of targets
# (gtest, gtest_main, gmock) serves both. A configure that includes it downloads googletest
# into the build directory's _deps once (network needed the first time).
include_guard(GLOBAL)

include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)
