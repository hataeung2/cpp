#include "memory_dump.h"

namespace alog {
  std::unique_ptr<ExceptionHandlerImpl> MemoryDump::impl_;

#ifdef _WIN32
#elif defined(__linux__)
  void signalHandler(int signum) {
    std::cerr << "Signal caught: " << signum << std::endl;

    std::signal(signum, SIG_DFL);

    std::raise(signum);

    // from RingBuffer
    MemoryDump::dump();
  }

  void ExceptionHandlerImpl_Linux::registerHandler() {
    std::signal(SIGSEGV, signalHandler);
  };
#endif
}//!namespace alog {