// Spec 070-25, KI-050: Windows Debug 레슨의 CRT 보고를 대화상자 대신 stderr로 보낸다.
// Spec 070-25, KI-050: Windows Debug lessons send CRT reports to stderr instead of a dialog.
//
// Debug CRT는 abort()와 assert 실패 때 모달 대화상자를 띄우고, 누를 때까지 프로그램이 끝나지 않는다.
// 그러면 smoke test와 tools/exercises.py check가 시간 제한까지 멈춘다. 여기서는 보고를 stderr 한 줄로 바꾸고
// Windows 오류 보고(_CALL_REPORTFAULT)를 끈다: 프로그램은 Release처럼 종료 코드 3으로 바로 끝난다.
// 디버거가 붙어 있으면 아무것도 바꾸지 않는다(대화상자의 Retry로 중단점에 들어갈 수 있게).
// The Debug CRT shows a modal dialog on abort() and on a failed assert, and the program does not end until
// someone clicks it, so smoke tests and tools/exercises.py check wait out their time limit. This file turns
// the report into one stderr line and switches off Windows Error Reporting (_CALL_REPORTFAULT): the program
// ends at once with exit code 3, as in Release. With a debugger attached nothing changes (Retry still breaks).

#if defined(_WIN32) && defined(_DEBUG)

// MACRO: keep <windows.h> small and free of the min/max macros
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <crtdbg.h>
#include <cstdlib>
#include <initializer_list>

#pragma warning(disable : 4073)
#pragma init_seg(lib)
// lib 세그먼트의 객체는 사용자 정적 객체보다 먼저 만들어지므로, 그 생성자에서 난 abort()도 여기를 거친다.
// Objects in the lib segment are constructed before user static objects, so an abort() in their
// constructors is reported this way too.

namespace {

struct CrtReportToStderr {
    CrtReportToStderr() noexcept {
        if (IsDebuggerPresent()) {
            return;
        }
        for (const int type : { _CRT_ERROR, _CRT_ASSERT }) {
            _CrtSetReportMode(type, _CRTDBG_MODE_FILE);
            _CrtSetReportFile(type, _CRTDBG_FILE_STDERR);
        }
        // 메시지(_WRITE_ABORT_MSG)는 남기고 오류 보고만 끈다
        // Keep the message (_WRITE_ABORT_MSG), switch off only the fault report
        _set_abort_behavior(0, _CALL_REPORTFAULT);
    }
};

const CrtReportToStderr kCrtReportToStderr;

}  // namespace

#endif
