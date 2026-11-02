// Spec 090-06 AC-8, AC-9: Probe to verify console code page switching and restoration.

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include <fstream>
#include <iostream>
#include <string>
#include <string_view>

namespace {

std::string g_out_path;

void appendCodePage(std::string_view prefix) {
    if (g_out_path.empty()) {
        return;
    }
#ifdef _WIN32
    std::ofstream out(g_out_path, std::ios::app);
    if (out.is_open()) {
        out << prefix << "=" << GetConsoleOutputCP() << "\n";
    }
#endif
}

class ScopeProbe {
public:
    ~ScopeProbe() {
        appendCodePage("dtor");
    }
};

const ScopeProbe kScopeProbe;

}  // namespace

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "usage: console_cp_probe <out-file>\n";
        return 2;
    }

    g_out_path = argv[1];
    appendCodePage("run");
    std::cout << "한글 × µs ⏱\n";
    std::cout.flush();
    return 0;
}
