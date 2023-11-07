import sample_module;
#include <iostream>

int main(int argc, char* argv[])
{
  std::cout << sample_module::name() << "printed!" << std::endl;
  return 0;
}