#include "adefine.hpp"
#include "atime.hpp"




namespace alog {

class ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl() = default;
  virtual ~ExceptionHandlerImpl() = default;
public:
  virtual void registerHandler() PURE;
  void dump();
};
#ifdef _WIN32
class ExceptionHandlerImpl_Windows : public ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl_Windows() = default;
  virtual ~ExceptionHandlerImpl_Windows() = default;
public:
  virtual void registerHandler() final;
};

#elif defined(__linux__)
class ExceptionHandlerImpl_Linux : public ExceptionHandlerImpl {
public:
  ExceptionHandlerImpl_Linux() = default;
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
  static inline void dump() {
    impl_->dump();
  }
private:
  static inline void registerHandler() {
    impl_->registerHandler();
  }
  static std::unique_ptr<ExceptionHandlerImpl> impl_;
};


}//!namespace alog {


#ifdef _WIN32
  import <memory>;
  import <iostream>;
  import <fstream>;
  import <filesystem>;
  #define WIN32_LEAN_AND_MEAN 
  import <Windows.h>;
  import <format>;
  // import <DbgHelp.h>;
  // #pragma comment(lib, "Dbghelp.lib")
  LONG WINAPI crashHdler(EXCEPTION_POINTERS* exceptionInfo) {
    std::cout << "program crashed!" << std::endl;
    
    // from RingBuffer
    alog::MemoryDump::dump();
    return EXCEPTION_CONTINUE_SEARCH;
  }
  void alog::ExceptionHandlerImpl_Windows::registerHandler() {
    SetUnhandledExceptionFilter(crashHdler);
  };


#elif defined(__linux__)
  #include <memory>
  #include <iostream>
  #include <fstream>
  #include <filesystem>
  #include <fmt/core.h>
  #include <csignal>
  void signalHandler(int signum) {
    std::cerr << "program crashed! " << signum << std::endl;
    std::signal(signum, SIG_DFL);
    std::raise(signum);

    // from RingBuffer
    alog::MemoryDump::dump();
  }

  void alog::ExceptionHandlerImpl_Linux::registerHandler() {
    std::signal(SIGSEGV, signalHandler);
  };

#endif

namespace fs = std::filesystem;

namespace alog {

  std::unique_ptr<ExceptionHandlerImpl> MemoryDump::impl_;


  void ExceptionHandlerImpl::dump() {
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

}//!namespace alog {