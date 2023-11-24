#include <iostream>
#include "sample/cond_var.hpp"
#include "sample/double_dispatch.hpp"
using namespace std;

#include "adefine.hpp"
#ifdef _WIN32
import alog;
import sample_module;
#else
#include "alog.h"
#endif

// libraries still have to use #include. ?
#include "shape.h"
#include "sound.h"

int main(int argc, char* argv[])
{
  REGISTER_MEMORY_DUMP_HANDLER;

  for (int i{0}; i < argc; ++i) {
    dlog("Argument: ", argv[i]);
  } 
  std::thread([&]{
    dlog("log from the thread 1");
  }).join();
  // cout << alog::DbgBuf::get();

#ifdef _WIN32
  cout << sample_module::name() << "printed!" << endl;
#else
  //
#endif
  
  
  // condition_variable_usage1();

  
  // double_dispatch
  SystemA<std::string> sa;
  SystemB<std::string> sb;
  sa.sendDataTo(sb, "hi B");
  sb.sendDataTo(sa, "hi A");




  // libshape.a
  Rectangle r(1, 2);
  std::cout << "rectangle size: " << r.GetSize() << std::endl;

  // libsound.so
  Sound s(10);
  std::cout << "sound volume: " << s.MakeNoize() << std::endl;




  // exception make to crash
  int* ptr = nullptr;
  *ptr = 0;

  std::thread([&]{
    dlog("log from the thread 2");
  }).join();

  return 0;
}