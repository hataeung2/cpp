#include <iostream>
#include "sample/cond_var.hpp"
#include "sample/double_dispatch.hpp"
using namespace std;

#include "atugcc/core/adefine.hpp"
#include "atugcc/core/alog.h"

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
  /**
   * @brief memory dump function adding
   *        used "dlog" definition for logging
   * 
   */
  REGISTER_MEMORY_DUMP_HANDLER;

  // log test with arguments
  // import alog; or #include "atugcc/core/alog.h" enables "dlog" definition
  for (int i{0}; i < argc; ++i) {
    atugcc::core::DbgBuf::log("Argument: " + std::string(argv[i]), atugcc::core::Level::Debug);
  } 
  auto t1 = thread([&]{
    for (auto i = 0; i < 125; ++i) {
      atugcc::core::DbgBuf::log("log from the thread 1", atugcc::core::Level::Debug);
    }
  });
  // cout << alog::DbgBuf::get();
  auto t2 = thread([&]{
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
  thread([&]{
    atugcc::core::DbgBuf::log("log from the thread 3", atugcc::core::Level::Debug);
  }).join();

  alog::MemoryDump::dump();
  return 0;
}