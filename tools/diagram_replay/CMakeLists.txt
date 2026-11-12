# Tool of spec 070-07: diagram replay (N-th event diagram generator)
# The web server builds it together with a lesson and runs it for the Diagrams tab replay.
add_executable(atugcc_diagram_replay main.cpp)
target_include_directories(atugcc_diagram_replay PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(atugcc_diagram_replay PRIVATE atugcc_headers atugcc_core)
set_target_properties(atugcc_diagram_replay PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/tools")
