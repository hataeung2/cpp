#ifndef __MEMORY_DUMP__
#define __MEMORY_DUMP__

#define PURE =0

#ifdef _WIN32
import <memory>;
import <iostream>;
import <fstream>;
import <filesystem>;
import <format>;
#define aformat std::format
import "ring_buffer.h";
#else
#include <memory>
#include <iostream>
#include <fstream>
#include <filesystem>
#include <fmt/core.h>
#define aformat fmt::format
#include "ring_buffer.h"
#endif

#include "atime.hpp"

#ifdef _WIN32
import <Windows.h>;
LONG WINAPI crashHdler(EXCEPTION_POINTERS* exceptionInfo);
#elif defined(__linux__)
#include <csignal>
void signalHandler(int signum);
#endif

namespace fs = std::filesystem;

namespace alog {

class ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl() {}
  virtual ~ExceptionHandlerImpl() = default;
public:
  virtual void registerHandler() PURE;
  void dump() {
    const char* dirPath = "log";
    using tstmp = TimeStamp;
    std::string filePath = aformat("log/dump{}.log", tstmp::str(tstmp::OPTION::eNothing));
    
    if (!fs::exists(filePath)) { fs::remove(filePath); }
    if (!fs::exists(dirPath)) { fs::create_directory(dirPath); }
    std::cerr << filePath << std::endl;
    std::ofstream outFile(filePath);
    if (outFile.is_open()) {
      outFile << DbgBuf::get() << std::endl;
    } else {
      std::cerr << "Error opening dump file." << std::endl << DbgBuf::get() << std::endl;
    }
  };
};
#ifdef _WIN32
class ExceptionHandlerImpl_Windows : public ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl_Windows() {}
  virtual ~ExceptionHandlerImpl_Windows() = default;
public:

  virtual void registerHandler() final {
    SetUnhandledExceptionFilter(crashHdler);
  };
};

#elif defined(__linux__)
class ExceptionHandlerImpl_Linux : public ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl_Linux() {}
  virtual ~ExceptionHandlerImpl_Linux() = default;
public:
  virtual void registerHandler() final;
};
#endif


class MemoryDump {
public:
  MemoryDump() {
#ifdef _WIN32
    impl_ = std::make_unique<ExceptionHandlerImpl_Windows>();
#elif defined(__linux__)
    impl_ = std::make_unique<ExceptionHandlerImpl_Linux>();
#endif
    impl_->registerHandler();
  }
  ~MemoryDump() = default;
public:
  static void dump() {
    impl_->dump();
  }
private:
  static void registerHandler() {
    impl_->registerHandler();
  }
  static std::unique_ptr<ExceptionHandlerImpl> impl_;
};


}//!namespace alog {

  
#ifdef _WIN32
// import <DbgHelp.h>;
// #pragma comment(lib, "Dbghelp.lib")
LONG WINAPI crashHdler(EXCEPTION_POINTERS* exceptionInfo) {
  std::cout << "program crashed!" << std::endl;
  
  // from RingBuffer
  alog::MemoryDump::dump();

  return EXCEPTION_CONTINUE_SEARCH;
}
#endif


#endif//!__MEMORY_DUMP__