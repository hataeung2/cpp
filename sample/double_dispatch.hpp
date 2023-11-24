/**
 * @file double_dispatch.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-11-23
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#ifndef __DOUBLE_DISPATCH__
#define __DOUBLE_DISPATCH__

#include "adefine.hpp"
#include <string>
#include <iostream>



using Data = std::string;

template<typename T> class SystemA;
template<typename T> class SystemB;

template <typename T>
class SubSystem {
public:
  SubSystem() = default;
  virtual ~SubSystem() = default;
public:
  virtual void sendDataTo(SubSystem<T>& ss, const T& d);
  virtual void RecvDataFrom(const SystemA<T>& ss, const T& d) PURE;
  virtual void RecvDataFrom(const SystemB<T>& ss, const T& d) PURE;

  const T& getLastRecvd() const;
protected:
  void setLastRecvd(T& d);
private:
  T m_lastRecvd;
};

template <typename T>
class SystemA : public SubSystem<T> {
public:
  SystemA() = default;
  virtual ~SystemA() = default;

public:
  virtual void sendDataTo(SubSystem<T>& ss, const T& d) final;
  virtual void RecvDataFrom(const SystemA<T>& ss, const T& d) final;
  virtual void RecvDataFrom(const SystemB<T>& ss, const T& d) final;
};

template <typename T>
class SystemB : public SubSystem<T> {
public:
  SystemB() = default;
  virtual ~SystemB() = default;

public:
  virtual void sendDataTo(SubSystem<T>& ss, const T& d) final;
  virtual void RecvDataFrom(const SystemA<T>& ss, const T& d) final;
  virtual void RecvDataFrom(const SystemB<T>& ss, const T& d) final;
};

template <typename T>
void SubSystem<T>::sendDataTo(SubSystem<T>& ss, const T& d) {
  ss.setLastRecvd(const_cast<T&>(d));
}

template <typename T>
inline const T &SubSystem<T>::getLastRecvd() const {
  return m_lastRecvd;
}

template <typename T>
void SubSystem<T>::setLastRecvd(T &d) {
  m_lastRecvd = d;
}



template <typename T>
void SystemA<T>::sendDataTo(SubSystem<T>& ss, const T& d) {
  SubSystem<T>::sendDataTo(ss, d);
  ss.RecvDataFrom(*this, d);
}
template <typename T>
void SystemA<T>::RecvDataFrom(const SystemA<T>& ss, const T& d) {
  std::cout << "A got data from A. typeid: " << typeid(d).name() << std::endl;
}
template <>
void SystemA<std::string>::RecvDataFrom(const SystemA<std::string>& ss, const std::string& d) {
    std::cout << "A got data from A (specialized for std::string): " << d << std::endl;
}
template <typename T>
void SystemA<T>::RecvDataFrom(const SystemB<T>& ss, const T& d) {
  std::cout << "A got data from B. typeid: " << typeid(d).name() << std::endl;
}
template <>
void SystemA<std::string>::RecvDataFrom(const SystemB<std::string>& ss, const std::string& d) {
    std::cout << "A got data from B (specialized for std::string): " << d << std::endl;
}

template <typename T>
void SystemB<T>::sendDataTo(SubSystem<T>& ss, const T& d) {
  SubSystem<T>::sendDataTo(ss, d);
  ss.RecvDataFrom(*this, d);
}
template <typename T>
void SystemB<T>::RecvDataFrom(const SystemA<T>& ss, const T& d) {
  std::cout << "B got data from A. typeid: " << typeid(d).name() << std::endl;
}
template <>
void SystemB<std::string>::RecvDataFrom(const SystemA<std::string>& ss, const std::string& d) {
    std::cout << "B got data from A (specialized for std::string): " << d << std::endl;
}
template <typename T>
void SystemB<T>::RecvDataFrom(const SystemB<T>& ss, const T& d) {
  std::cout << "B got data from B. typeid: " << typeid(d).name() << std::endl;
}
template <>
void SystemB<std::string>::RecvDataFrom(const SystemB<std::string>& ss, const std::string& d) {
    std::cout << "B got data from B (specialized for std::string): " << d << std::endl;
}


#endif//! __DOUBLE_DISPATCH__