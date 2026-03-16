/**
 * @file decorator.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-07
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#include <iostream>
#include <memory>
using namespace std;
namespace decorator {

class Product {
public:
  Product() = default;
  virtual ~Product() = default;
public:
  virtual const string someFunc() {
    return "origin";
  }
};

class Extended : public Product {
public:
  Extended() = default;
  virtual ~Extended() = default;
public:
  virtual const string someFunc() final {
    return "extend";
  }
};



class ADecorator : public Product {
public:
  ADecorator(shared_ptr<Product> prod) : prod_(prod) {}
  virtual ~ADecorator() = default;
public:
  virtual const string someFunc() =0;
protected:
  shared_ptr<Product> prod_;
};

class Deco1 : public ADecorator {
public:
  Deco1(shared_ptr<Product> prod) : ADecorator(prod) {}
  virtual ~Deco1() = default;
public:
  virtual const string someFunc() {
    return prod_->someFunc() + " deco1 wrapped";
  }
};

class Deco2 : public ADecorator {
public:
  Deco2(shared_ptr<Product> prod) : ADecorator(prod) {}
  virtual ~Deco2() = default;
public:
  virtual const string someFunc() {
    return prod_->someFunc() + " deco2 wrapped";
  }
};



void decoratorSample() {
using ProdPtr = shared_ptr<Product>;
  
  // origin
  ProdPtr origin{ make_shared<Product>() };
  cout << origin->someFunc() << endl;
  
  // extend
  ProdPtr extend{ make_shared<Extended>() };
  cout << extend->someFunc() << endl;

  // origin wrapped with deco1
  ProdPtr d1 { make_shared<Deco1>(ProdPtr(origin)) };
  cout << d1->someFunc() << endl;

  // extend wrapped with deco2
  ProdPtr d2 { make_shared<Deco2>(ProdPtr(extend)) };
  cout << d2->someFunc() << endl;

  // (origin wrapped with deco1) wrapped with deco1
  ProdPtr d1_add_deco1 { make_shared<Deco1>(ProdPtr(d1)) };
  cout << d1_add_deco1->someFunc() << endl;

  // ((origin wrapped with deco1) wrapped with deco1) wrapped with deco2
  ProdPtr d1_add_deco1_deco2 { make_shared<Deco2>(ProdPtr(d1_add_deco1)) };
  cout << d1_add_deco1_deco2->someFunc() << endl;

}


}//!namespace decorator {