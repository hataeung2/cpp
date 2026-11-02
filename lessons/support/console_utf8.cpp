// Spec 090-06, KI-011: 레슨 콘솔 UTF-8 출력 설정 및 복원.
//
// 레슨 실행 파일의 출력은 UTF-8(한글 로그, '×', 'µs', '⏱' 등)로 구성되어 있어
// cp949 등 비UTF-8 Windows 콘솔에서 실행 시 글자가 깨집니다.
// 코드 페이지는 프로세스가 아니라 콘솔 장치 자체의 상태이므로, 정상 종료 시 원래 코드 페이지로 복원합니다.
// 크래시나 강제 종료(TerminateProcess 등) 시에는 복원되지 않습니다.
// 표준 출력이 실제 콘솔일 때만 변경하며, 출력 코드 페이지(GetConsoleOutputCP)만 변경하고 입력은 건드리지 않습니다.

#ifdef _WIN32

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#pragma warning(disable : 4073)
#pragma init_seg(lib)
// objects in the lib segment are constructed before and destroyed after ordinary (user)
// static objects, so lines written by other static objects' destructors still go out as UTF-8;
// the C++ standard leaves the order between translation units unspecified.

namespace {

class ConsoleUtf8 {
public:
    ConsoleUtf8() noexcept {
        const HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE);
        if (out == nullptr || out == INVALID_HANDLE_VALUE) {
            return;
        }
        if (GetFileType(out) != FILE_TYPE_CHAR) {
            return;
        }
        DWORD mode = 0;
        if (!GetConsoleMode(out, &mode)) {
            return;
        }

        const UINT cp = GetConsoleOutputCP();
        if (cp != 0 && cp != CP_UTF8 && SetConsoleOutputCP(CP_UTF8)) {
            previous_ = cp;
        }
    }

    ~ConsoleUtf8() {
        if (previous_ != 0) {
            SetConsoleOutputCP(previous_);
        }
    }

    ConsoleUtf8(const ConsoleUtf8&) = delete;
    ConsoleUtf8& operator=(const ConsoleUtf8&) = delete;
    ConsoleUtf8(ConsoleUtf8&&) = delete;
    ConsoleUtf8& operator=(ConsoleUtf8&&) = delete;

private:
    UINT previous_ = 0;
};

const ConsoleUtf8 kConsoleUtf8;

}  // namespace

#else
// On non-Windows platforms (e.g. Linux), this translation unit compiles to nothing.
#endif
