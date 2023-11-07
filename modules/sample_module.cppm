// declare it is a module
module;

// includes
#include <string>

// export module with its name
export module sample_module;



// internal functions
const char* _getName() { return "sample module's name"; }

// export with namespace
export namespace sample_module {
  std::string name() { return std::string{ _getName() }; }
}