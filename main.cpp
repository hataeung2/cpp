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


#include "sample/sql_postgre.hpp"


int main(int argc, char* argv[])
{
  // for memory dump
  REGISTER_MEMORY_DUMP_HANDLER;

  // log test with arguments
  for (int i{0}; i < argc; ++i) {
    dlog("Argument: ", argv[i]);
  } 
  thread([&]{
    dlog("log from the thread 1");
  }).join();
  cout << alog::DbgBuf::get();

#ifdef _WIN32
  cout << sample_module::name() << "printed!" << endl;
#else
  //
#endif
  
  // 
  condition_variable_usage1();


  // postgre sql test with PQXX
  try {
    postgreConnectionTest();
  } catch (exception& e) {
    cout << "exception caught" << e.what() << endl;
  }

  
  // double_dispatch
  SystemA<string> sa;
  SystemB<string> sb;
  sa.sendDataTo(sb, "hi B");
  sb.sendDataTo(sa, "hi A");




  // libshape.a(lib)
  Rectangle r(1, 2);
  cout << "rectangle size: " << r.GetSize() << endl;

  // libsound.so(dll)
  Sound s(10);
  cout << "sound volume: " << s.MakeNoize() << endl;




  // exception make to crash for memory dump test
  int* ptr = nullptr;
  *ptr = 0;

  // log test with arguments (for memory dump test to check no log after the exception)
  thread([&]{
    dlog("log from the thread 2");
  }).join();


  return 0;
}