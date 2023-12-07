/**
 * @file injection.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-05
 * 
 * @copyright Copyright (c) 2023
 * 
 */
#include <string>
#include <fstream>
namespace injection {

class ILogger {
public:
  ILogger() = default;
  virtual ~ILogger() = default;
  virtual void entry(const std::string data) =0;
};

class SampleInjectedLogger1 : public ILogger {
public:
  explicit SampleInjectedLogger1(std::string_view filename);
  virtual ~SampleInjectedLogger1();
  virtual void entry(const std::string data) final;
private:
  std::ofstream ostream_;
};

SampleInjectedLogger1::SampleInjectedLogger1(std::string_view filename) {
  ostream_.open(filename.data(), std::ios_base::trunc);
  if (!ostream_.good()) {
    throw std::runtime_error { "Unable to initialize the SampleInjectedLogger1!" };
  }
}

SampleInjectedLogger1::~SampleInjectedLogger1() {
  ostream_ << "SampleInjectedLogger1 shutting down" << endl;
  ostream_.close();
}

void SampleInjectedLogger1::entry(const std::string data) {
  ostream_ << data << std::endl;
}

class SampleInjectedLogger2 : public ILogger {
public:
  explicit SampleInjectedLogger2(std::string_view filename);
  virtual ~SampleInjectedLogger2();
  virtual void entry(const std::string data) final;
private:
  std::ofstream ostream_;
};

SampleInjectedLogger2::SampleInjectedLogger2(std::string_view filename) {
  ostream_.open(filename.data(), std::ios_base::trunc);
  if (!ostream_.good()) {
    throw std::runtime_error { "Unable to initialize the SampleInjectedLogger2!" };
  }
}

SampleInjectedLogger2::~SampleInjectedLogger2() {
  ostream_ << "SampleInjectedLogger2 shutting down" << endl;
  ostream_.close();
}

void SampleInjectedLogger2::entry(const std::string data) {
  ostream_ << data << std::endl;
}




class Subsystem {
public:
  Subsystem(ILogger& logger) : logger_(logger) { }
  ~Subsystem() = default;
public:
  void doSomething() {
    logger_.entry("Hello. This is dependency injected logger.");
  }
private:
  ILogger& logger_;
};


void injectionSample() {
  // Using Dependency Injection, 
  // Subsystem doesn't have to directly change the Logger classes's name in it.
  // => loose coupling

  SampleInjectedLogger1 logger1{ "sample_injected_logger1.out" };
  Subsystem ss1(logger1);
  ss1.doSomething();

  SampleInjectedLogger2 logger2{ "sample_injected_logger2.out" };
  Subsystem ss2(logger2);
  ss1.doSomething();
}

}//!namespace injection {