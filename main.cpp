#include <iostream>
#include "src/cond_var.hpp"
using namespace std;

#include "adefine.hpp"
#ifdef _WIN32
import alog;
import sample_module;
#else
#include "alog.h"
#endif


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

  // exception make to crash
  int* ptr = nullptr;
  *ptr = 0;

  std::thread([&]{
    dlog("log from the thread 2");
  }).join();

  return 0;
}