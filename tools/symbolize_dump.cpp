#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <DbgHelp.h>
#include <iostream>
#include <fstream>
#include <vector>
#include <algorithm>

#pragma comment(lib, "Dbghelp.lib")

int main(int argc, char** argv) {
  if (argc < 3) {
    std::cerr << "Usage: symbolize_dump <dump-file> <exe-path>\n";
    return 1;
  }
  const char* dumpPath = argv[1];
  const char* exePath = argv[2];

  std::ifstream in(dumpPath, std::ios::binary);
  if (!in) {
    std::cerr << "Failed to open dump file: " << dumpPath << "\n";
    return 2;
  }
  std::vector<char> data((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  const std::string marker = "--CONTEXT-BINARY--\n";
  auto it = std::search(data.begin(), data.end(), marker.begin(), marker.end());
  if (it == data.end()) {
    std::cerr << "Context marker not found in dump file\n";
    return 3;
  }
  size_t idx = std::distance(data.begin(), it) + marker.size();
  if (data.size() < idx + sizeof(CONTEXT)) {
    std::cerr << "Dump does not contain a full CONTEXT struct\n";
    return 4;
  }
  CONTEXT ctx{};
  std::memcpy(&ctx, data.data() + idx, sizeof(CONTEXT));

#if defined(_M_X64) || defined(__x86_64__)
  DWORD64 ip = ctx.Rip;
#elif defined(_M_IX86) || defined(__i386__)
  DWORD64 ip = ctx.Eip;
#else
  #error Unsupported architecture for symbolization
#endif

  HANDLE hProc = GetCurrentProcess();
  // Initialize the symbol handler and allow it to enumerate the process modules
  if (!SymInitialize(hProc, NULL, TRUE)) {
    std::cerr << "SymInitialize failed: " << GetLastError() << "\n";
    return 5;
  }
  SymSetOptions(SYMOPT_LOAD_LINES | SYMOPT_UNDNAME);

  std::cout << "Context IP: 0x" << std::hex << ip << std::dec << "\n";

  // If the dump recorded module base and filename, use that base when loading
  // the module so SymFromAddr can resolve absolute IPs from the crash.
  const std::string modulesMarker = "--MODULES--\n";
  auto mit = std::search(data.begin(), data.end(), modulesMarker.begin(), modulesMarker.end());
  DWORD64 loadBase = 0;
  if (mit != data.end()) {
    size_t m_idx = std::distance(data.begin(), mit) + modulesMarker.size();
    if (data.size() >= m_idx + sizeof(uint64_t)) {
      uint64_t recBase = 0;
      std::memcpy(&recBase, data.data() + m_idx, sizeof(recBase));
      size_t name_start = m_idx + sizeof(recBase);
      auto name_end_it = std::find(data.begin() + name_start, data.end(), '\n');
      std::string recName;
      if (name_end_it != data.end()) {
        recName.assign(data.begin() + name_start, name_end_it);
      } else {
        recName.assign(data.begin() + name_start, data.end());
      }
      std::cout << "Recorded module base: 0x" << std::hex << recBase << std::dec << "\n";
      std::cout << "Recorded module filename: " << recName << "\n";
      loadBase = static_cast<DWORD64>(recBase);
    }
  }

  DWORD64 base = SymLoadModuleEx(hProc, NULL, exePath, NULL, loadBase, 0, NULL, 0);
  std::cout << "SymLoadModuleEx returned base: " << base << "\n";
  if (base == 0) {
    std::cerr << "SymLoadModuleEx failed: " << GetLastError() << "\n";
  }

  // Prepare SYMBOL_INFO
  constexpr size_t maxName = 1024;
  std::vector<char> symBuf(sizeof(SYMBOL_INFO) + maxName);
  PSYMBOL_INFO pSym = reinterpret_cast<PSYMBOL_INFO>(symBuf.data());
  pSym->SizeOfStruct = sizeof(SYMBOL_INFO);
  pSym->MaxNameLen = static_cast<ULONG>(maxName);

  DWORD64 displacement = 0;
  if (SymFromAddr(hProc, ip, &displacement, pSym)) {
    std::cout << "Symbol: " << pSym->Name << " + 0x" << std::hex << displacement << std::dec << "\n";
  } else {
    std::cerr << "SymFromAddr failed: " << GetLastError() << "\n";
  }

  IMAGEHLP_LINE64 line{};
  DWORD dwDisp = 0;
  if (SymGetLineFromAddr64(hProc, ip, &dwDisp, &line)) {
    std::cout << "Source: " << line.FileName << ":" << line.LineNumber << "\n";
  } else {
    std::cerr << "SymGetLineFromAddr64 failed: " << GetLastError() << "\n";
  }

  SymCleanup(hProc);
  return 0;
}
#else
#error This tool only builds on Windows
#endif
