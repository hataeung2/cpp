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
#include "sample/design_pattern/state.hpp"
#include "sample/design_pattern/injection.hpp"
#include "sample/design_pattern/observer.hpp"
#include "sample/design_pattern/decorator.hpp"

int main(int argc, char* argv[])
{
  /**
   * @brief memory dump function adding
   *        used "dlog" definition for logging
   * 
   */
  REGISTER_MEMORY_DUMP_HANDLER;

  // log test with arguments
  // import alog; or #include "alog.h" enables "dlog" definition
  for (int i{0}; i < argc; ++i) {
    dlog("Argument: ", argv[i]);
  } 
  auto t1 = thread([&]{
    for (auto i = 0; i < 125; ++i) {
      dlog("log from the thread 1");
    }
  });
  // cout << alog::DbgBuf::get();
  auto t2 = thread([&]{
    for (auto i = 0; i < 125; ++i) {
      dlog("log from the thread 2");
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
  decorator::decoratorSample();




  /**
   * @brief exception make to crash for memory dump test
   * 
   */
  // int* ptr = nullptr;
  // *ptr = 0;

  // log test with arguments (for memory dump test to check no log after the exception)
  thread([&]{
    dlog("log from the thread 3");
  }).join();

  alog::MemoryDump::dump();
  return 0;
}