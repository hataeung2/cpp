# atugcc playground

## Where you are
A **local page** for editing, building and running the `lessons/` folder of the atugcc repository in the browser.
- There is no separate copy. Saving here changes the repository's files; VS Code shows the same content, and `git diff` shows the change.
- Builds use the repository's CMake presets (`linux-x64-playground`, and `linux-x64-playground-release` for lessons that run long). They are the same targets as a local lesson build.
- This text is a repository file too. Click the path above it to open it in the editor and change it.

## Two layers: the library and the lessons
| | Library | Lessons |
|---|---|---|
| Where | `include/atugcc/`, `src/` (CMake target `atugcc_core`) | `lessons/` |
| What | Core features other projects use as they are: logging, ring buffer, time, error handling, pattern skeletons (State and others), Tracer (visualization, span timing) | Practice applying the library to a situation: applying and adapting patterns, structure, real-world use. And the C++ syntax and idioms underneath |
| Here | 🔒 read-only. Change it in VS Code | Edit and Run |
| A change | reaches every lesson from the next Run (no copies) | affects that lesson only |

Library examples: [logger.hpp](/include/atugcc/core/logger.hpp), [state.hpp](/include/atugcc/pattern/state.hpp), [visualizer.hpp](/include/atugcc/pattern/visualizer.hpp) (Tracer)

## What you do here
1. **Read**: see how the library is used in a lesson's README and code. The editor opens the lesson's sources together with the units and library headers it uses.
2. **Change it**: edit the code and press ▶ Run (Ctrl+Enter). Modified tabs are saved, then the lesson is built and run. Compiler errors are marked in the editor.
3. **See it**: the tabs on the right
   - **Output**: what the program prints, line by line while it runs.
   - **Events**: Tracer events in order. Click one to go to its source line.
   - **Diagrams**: Mermaid diagrams made by the Tracer. They appear when the program ends normally.
   - **Timings**: code-range times measured with spans, and the change against the previous run. They also appear as `⏱` at the end of the line in the editor.

   Events, Diagrams and Timings fill in when the lesson uses the Tracer. The lesson code needs no extra setup.
4. **Find**: the search box above the tree finds lessons by title or by feature (`jthread`, `logger.hpp`, `state machine`, also in Korean). Press `/` to jump to it, Enter to open the first result. The tags above a lesson's README search for that tag.
5. **Language**: the `한` / `EN` button at the top switches the page between Korean and English. READMEs without an English version are shown in Korean.

## Order
The tree on the left is the track order.
1. **01_essentials**: core features, everyday syntax (lambdas, concurrency), thread and log management. Example: [lambda capture](/lessons/tracks/01_essentials/01_lambda_capture/README.en.md)
2. **02_patterns**: applying and adapting patterns to a situation. Example: [device state machine](/lessons/tracks/02_patterns/01_device_state_machine/README.en.md)

The **units** at the bottom of the tree are code that several lessons share. "Used by: …" lists the lessons that use a unit.

## What you cannot do here
- **Edit the library**: change `include/` and `src/` in VS Code.
- **Open it to others**: it listens on `127.0.0.1` only. The server builds and runs lesson code as it is, so it is never opened to another network.
- **Build for Windows (MSVC)**: the page builds with Clang in WSL only. Lessons must build without warnings on both compilers, so build a changed lesson with a Windows preset as well.

## Making a lesson
- What code goes where, and the steps to add a lesson: the Workflow section of the repository [README.md](/README.md) (Korean)
- Manifest format and writing guide: [lessons/README.md](/lessons/README.md) (Korean)
