#ifndef __MEMORY_DUMP__
#define __MEMORY_DUMP__

#define PURE =0

import <memory>;
import <iostream>;
import "ring_buffer.h";

#ifdef _WIN32
import <Windows.h>;
LONG WINAPI crashHdler(EXCEPTION_POINTERS* exceptionInfo);
#endif


namespace alog {

class ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl() {}
  virtual ~ExceptionHandlerImpl() = default;
public:
  virtual void registerHandler() PURE;
  void dump() {
    std::cerr << DbgBuf::get() << std::endl;
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
  virtual void registerHandler() final {

  };
#endif


class MemoryDump {
public:
  MemoryDump() {
#ifdef _WIN32
    impl_ = std::make_unique<ExceptionHandlerImpl_Windows>();
#elif defined(__linux__)
    
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
std::unique_ptr<ExceptionHandlerImpl> MemoryDump::impl_;


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