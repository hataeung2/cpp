# Plan: 090-03 vcpkg manifest로 Boost 자동 공급

- Spec: [/docs/specs/090_03_vcpkg_manifest.md](/docs/specs/090_03_vcpkg_manifest.md) (approved 2026-10-28)
- Branch: `feature/090-03-vcpkg-manifest` (from `main` after 090-01)

## Files
- [NEW] `/vcpkg.json`: `boost-lockfree`
- [NEW] `/vcpkg-configuration.json`: git registry `microsoft/vcpkg`, baseline = release 2026.07.29 commit
- [MODIFY] `/CMakeLists.txt`: toolchain comment (bundled vcpkg + manifest)
- [MODIFY] `/README.md`, `/.agent/rules/config.md`: manifest workflow, failure rows
- [MODIFY] `/docs/known_issues.md`: KI-007 CLOSED
- [MODIFY] `/docs/tasks/agent_todo.md`: 090-03 added; 020-04 approved (user, same day)
- [MODIFY] `/docs/specs/020_04_diagram_readability.md`: `approved: 2026-10-28`

## Units
| Unit | File | Change | Check | Risky | Author | Reviewer | Status |
|---|---|---|---|---|---|---|---|
| U1 | `vcpkg.json`, `vcpkg-configuration.json` | manifest + pinned registry | Windows configure installs Boost; build `/W4 /WX`; suite | no | lead | `cpp-reviewer` | done |
| U2 | `README.md`, `config.md`, `CMakeLists.txt` comment | docs | `lint_docs.py` exit 0 | no | lead | `cpp-reviewer` | done |
