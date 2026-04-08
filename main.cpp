#include <iostream>
#include "sample/cond_var.hpp"
#include "sample/double_dispatch.hpp"
using namespace std;

#include "atugcc/core/adefine.hpp"
#include "atugcc/core/alog.h"
#include "atugcc/core/error.hpp"

#include <thread>
#include <vector>
#include <chrono>
#include <filesystem>
#include <csignal>
#include <atomic>
#include <string>
#if defined(__linux__) || defined(__unix__) || defined(__APPLE__)
#include <unistd.h>
#endif

#ifdef _WIN32
import sample_module;
#endif


// libraries still have to use #include. ?
#include "atugcc/libs/shape.h"
#include "atugcc/libs/sound.h"

#ifdef ATUGCC_ENABLE_PQXX
#include "sample/sql_postgre.hpp"
#endif
#include "atugcc/pattern/state.hpp"
#include "atugcc/pattern/injection.hpp"
#include "atugcc/pattern/observer.hpp"
#include "atugcc/pattern/decorator.hpp"
#include "atugcc/pattern/factory.hpp"
#include "atugcc/pattern/command.hpp"
#include "atugcc/pattern/iterator_concept.hpp"

int main(int argc, char* argv[])
{
  std::cout << "hi" << std::endl;

  // Register global crash/signal handler that will attempt to write a
  // prepared crash dump. This macro is project-provided and must be
  // declared before using MemoryDump APIs.
  REGISTER_MEMORY_DUMP_HANDLER;

  // Simple CLI for running scenarios. Supported flags (examples):
  //  --prepare-dump <path>    : Prepare a dump target file for immediate dump
  //  --stress <threads> <msg> : Run a logging stress test (threads, messages)
  //  --dump-now               : Call MemoryDump::dump() to write a dump now
  //  --trigger-segfault       : Raise SIGSEGV to exercise handler (POSIX)

  // Minimal, manual arg parsing for convenience.
  std::filesystem::path preparedPath;
  int stressThreads = 0;
  int stressMsgs = 0;
  bool doDumpNow = false;
  bool doTriggerSegfault = false;

  for (int i = 1; i < argc; ++i) {
    std::string a(argv[i]);
    if (a == "--prepare-dump" && i + 1 < argc) {
      preparedPath = argv[++i];
    } else if (a == "--stress" && i + 2 < argc) {
      stressThreads = std::stoi(argv[++i]);
      stressMsgs = std::stoi(argv[++i]);
    } else if (a == "--dump-now") {
      doDumpNow = true;
    } else if (a == "--trigger-segfault") {
      doTriggerSegfault = true;
    }
  }

  // If requested, prepare the dump file/handle for the current platform.
  if (!preparedPath.empty()) {
#ifdef _WIN32
    // Windows: prepare by wide-string path
    std::wstring wp = preparedPath.wstring();
    auto res = alog::MemoryDump::prepareDumpFileWin(wp);
    if (!res.has_value()) {
      std::cerr << "prepareDumpFileWin failed\n";
    } else {
      std::cout << "Prepared dump HANDLE at: " << preparedPath << std::endl;
    }
#else
    auto res = alog::MemoryDump::prepareDumpFile(preparedPath);
    if (!res.has_value()) {
      std::cerr << "prepareDumpFile failed\n";
    } else {
      std::cout << "Prepared dump FD at: " << preparedPath << std::endl;
    }
#endif
  }

  // Example: record the provided argv values into the thread-local buffers
  for (int i{0}; i < argc; ++i) {
    atugcc::core::DbgBuf::log("Argument: " + std::string(argv[i]), atugcc::core::Level::Debug);
  }

  // If stress requested, start worker threads that log many messages.
  if (stressThreads > 0 && stressMsgs > 0) {
    std::cout << "Starting stress test: " << stressThreads << " threads, " << stressMsgs << " messages each\n";
    std::vector<std::thread> thr;
    std::atomic<int> counter{0};
    for (int t = 0; t < stressThreads; ++t) {
      thr.emplace_back([t, stressMsgs, &counter]{
        for (int m = 0; m < stressMsgs; ++m) {
          // Include thread id and sequence number to aid parser/debug
          std::string txt = "[T" + std::to_string(t) + "] msg " + std::to_string(m);
          atugcc::core::DbgBuf::log(txt, atugcc::core::Level::Info);
          ++counter;
          // tiny sleep to spread writes a bit
          std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
      });
    }
    for (auto &th : thr) th.join();
    std::cout << "Stress test finished, total messages: " << counter.load() << std::endl;
  }

  // Light-weight example threads from original main preserved for manual testing.
  auto t1 = std::thread([&]{
    for (auto i = 0; i < 125; ++i) {
      atugcc::core::DbgBuf::log("log from the thread 1", atugcc::core::Level::Debug);
    }
  });
  // cout << alog::DbgBuf::get();
  auto t2 = std::thread([&]{
    for (auto i = 0; i < 125; ++i) {
      atugcc::core::DbgBuf::log("log from the thread 2", atugcc::core::Level::Debug);
    }
  });

  t1.join();
  t2.join();

  /**
   * @brief PostgreSQL tests with PQXX
   * 
   */
  // // connect & select
  // try {
  //   postgreConnectionTest();
  // } catch (exception& e) {
  //   cout << "exception caught" << e.what() << endl;
  // }


  /**
   * @brief simply implemented module
   * 
   */
// #ifdef _WIN32
//   cout << sample_module::name() << "printed!" << endl;
// #else
//   //
// #endif


  /**
   * @brief simply implemented libraries 
   *        .a(lib) for shape
   *        .so(dll) for sound
   */

  // // libshape.a(lib)
  // Rectangle r(1, 2);
  // cout << "rectangle size: " << r.GetSize() << endl;

  // // libsound.so(dll)
  // Sound s(10);
  // cout << "sound volume: " << s.MakeNoize() << endl;




  
  
  /**
   * @brief condition variable usage for sync
   * 
   */
  // condition_variable_usage1();



  


  /**
   * @brief C++20 features, Design patterns
   * 
   */
  // //
  // // double_dispatch
  // //
  // SystemA<string> sa;
  // SystemB<string> sb;
  // sa.sendDataTo(sb, "hi B");
  // sb.sendDataTo(sa, "hi A");

  // //
  // // state pattern
  // //
  // astate::stateChangeSample();

  // //
  // // observer pattern
  // //
  // observer::observerSample();


  // //
  // // dependency injection
  // //
  // injection::injectionSample();


  // //
  // // decorator pattern
  // //
  // decorator::decoratorSample();


  // //
  // // factory patterns (abstract, factory method)
  // //
  // factory::factorySample();

  // //
  // // command pattern
  // //
  // command::commandSample();

  // //
  // // iterator pattern concept.
  // //
  iterator_concept::iteratorSample();


  /**
   * @brief exception make to crash for memory dump test
   * 
   */
  // int* ptr = nullptr;
  // *ptr = 0;

  // log test with arguments (for memory dump test to check no log after the exception)
  std::thread([&]{
    atugcc::core::DbgBuf::log("log from the thread 3", atugcc::core::Level::Debug);
  }).join();

  // If requested, either trigger a crash (SIGSEGV) to exercise the immediate
  // dump path (must have prepared a dump target beforehand), or perform a
  // non-crashing dump via MemoryDump::dump().
  if (doTriggerSegfault) {
  #if defined(__linux__) || defined(__unix__) || defined(__APPLE__)
    std::cout << "Raising SIGSEGV to exercise crash handler (use --prepare-dump first)" << std::endl;
    std::raise(SIGSEGV);
  #elif defined(_WIN32)
    std::cout << "Triggering access violation to exercise crash handler (use --prepare-dump first)" << std::endl;
    volatile int* p = nullptr;
    *p = 0;
  #else
    std::cerr << "--trigger-segfault unsupported on this build." << std::endl;
  #endif
  }

  if (doDumpNow) {
    // If a prepared FD exists (from --prepare-dump), prefer the immediate
    // async-safe path which writes raw blocks directly to that FD. Otherwise
    // fall back to the higher-level MemoryDump::dump() which writes a file
    // via the normal (non-handler) flow.
    int fd = alog::MemoryDump::getDumpFd();
    if (fd >= 0) {
      // Write a minimal header so parse_dump.py and other tools can
      // recognize the file before the raw binary blocks.
#if defined(__linux__) || defined(__unix__) || defined(__APPLE__)
      char timebuf[64] = {0};
      std::time_t tnow = std::time(nullptr);
      if (std::gmtime(&tnow)) {
        std::strftime(timebuf, sizeof(timebuf), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&tnow));
      }
      std::string hdr = "DUMP-V1\n";
      hdr += std::string("Timestamp: ") + timebuf + "\n";
      hdr += std::string("PID: ") + std::to_string(::getpid()) + "\n";
      hdr += std::string("TID: main\nEvent-Type: manual\nEvent-Code: DUMP\n\n--BINARY-BLOCKS--\n");
      ssize_t wn = ::write(fd, hdr.data(), static_cast<size_t>(hdr.size()));
      (void)wn;
#endif
      atugcc::core::DbgBuf::dumpToFd(fd);
      std::cout << "DbgBuf::dumpToFd() wrote to prepared FD." << std::endl;
    } else {
      const auto dump_res = alog::MemoryDump::dump();
      if (!dump_res.has_value()) {
        std::cerr << "MemoryDump failed: " << atugcc::core::to_string(dump_res.error()) << std::endl;
      } else {
        std::cout << "MemoryDump::dump() completed." << std::endl;
      }
    }
  }

  return 0;
}