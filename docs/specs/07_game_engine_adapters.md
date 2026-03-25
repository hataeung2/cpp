# Spec: atugcc::engine Adapter Architecture

## Objective
Design a loosely coupled, adapter-based game engine core (`atugcc::engine`) that relies on established third-party libraries (e.g., GLFW, Vulkan/OpenGL, EnTT) rather than reinventing the wheel. The architecture must allow underlying backends to be seamlessly swapped out or upgraded without affecting the high-level game logic.

## Requirement Details

### Public API Surface
- `include/atugcc/engine/window_system.hpp`: C++20 Concept or interface for window context, swapchain, and input events.
- `include/atugcc/engine/rhi_system.hpp`: Interface for Render Hardware Interface (RHI).
- `include/atugcc/engine/ecs_world.hpp`: Facade/Wrapper around the Entity Component System.
- `include/atugcc/math/`: Lightweight wrapper or concept-based alias bridging to a robust math library (e.g., GLM).

### Internal Implementation  
- `src/engine/adapters/glfw_window.cpp` (GLFW implementation)
- `src/engine/adapters/opengl_rhi.cpp` / `vulkan_rhi.cpp` (RHI implementations)
- `src/engine/adapters/entt_ecs.cpp` (EnTT integration)

### Platform Specifics
- Native handles (e.g., `HWND` on Windows, `X11/Wayland` on Linux) should be accessible via `std::any` or tightly controlled void pointers for advanced users requiring Native OS APIs.

## C++ Standard Evolution
| Approach | Standard | Description |
|----------|----------|-------------|
| Legacy | C++11/14 | Virtual base classes with deep inheritance trees (`virtual void update() = 0;`) which add vtable overhead. |
| Modern | C++20 | Concept-based generic programming (`template<WindowSystem W>`) or `std::variant`/Type Erasure for tight loop performance while maintaining decoupling. |
| Latest | C++23 | Return types using `std::expected` for robust adapter initialization handling. `std::move_only_function` for input/event callbacks. |

## Edge Cases
- [x] Thread safety: RHI (Renderer) commands usually must be pushed or processed on the main thread/render thread. ECS updates can and should easily be multithreaded (via EnTT).
- [x] Resource lifetime / RAII: Ensure C-styled third-party handles (e.g., `GLFWwindow*`) are strictly managed by smart pointers with custom deleters or RAII wrappers.
- [ ] Template instantiation / Compilation time: Crucially, use the PIMPL idiom or pure abstract interfaces to hide heavy third-party headers (like `<vulkan/vulkan.h>` or `<entt/entt.hpp>`) from `include/atugcc/engine/`. Otherwise, the user game code compile times will be devastated.
- [ ] ODR violations: Ensure any static adapter registries are carefully exported if compiled as a shared library.

## Dependencies & Adapters
- **Window/Input**: GLFW (preferred for cross-platform) or SDL3.
- **ECS (Entity Component System)**: EnTT.
- **Graphics**: OpenGL (GLAD) / Vulkan.
- **Math**: GLM.

## Technical Constraints
- Compiler: MSVC (VS 2026) / GCC (latest stable)
- CMake: 3.26+
- C++ Standard: C++23 (C++20 minimum)

## Context & References
- [Tasks](/docs/tasks/agent_todo.md)

## Implementation Plan
- [ ] Step 1: Add `FetchContent` to `CMakeLists.txt` for GLFW, EnTT, GLM.
- [ ] Step 2: Define C++20 `WindowSystem` concept and implement `atugcc::adapter::GlfwWindow` using PIMPL.
- [ ] Step 3: Implement `atugcc::engine::EcsWorld` wrapping `entt::registry` internally.
- [ ] Step 4: Write `engine_app` base class that initializes the adapter system and runs the main loop.
- [ ] Step 5: Verify the engine loop initializing, running at 60Hz, and tearing down safely.

## Verification Plan
- [ ] CMake build: `cmake --build build --config Debug`
- [ ] Tests: Write a basic GoogleTest `engine_core_test` that initializes the system, spawns an entity, assigns a dummy component, and ticks the engine loop a few times. `ctest --output-on-failure -C Debug`
- [ ] Code Quality: Zero warnings at `/W3` (MSVC) or `-Wall` (GCC).
