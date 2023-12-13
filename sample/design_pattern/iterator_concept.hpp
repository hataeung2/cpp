/**
 * @file iterator.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-12
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#include <iostream>
#include <memory>
#include <list>
using namespace std;

namespace iterator_concept {



struct Data {
  Data() {}
  Data(const string d) : d_(d) {}
  const string operator()() { return d_; }
  string d_;
};

class Iterator {
public:
  Iterator() = default;
  virtual ~Iterator() = default;
public:
  virtual string operator*() =0;
  virtual const bool hasNext() =0;
  virtual shared_ptr<Data> operator++() =0;
};



class Impl1Iter : public Iterator {
public:
  Impl1Iter(const Data* const items, const int itemcnt) 
  : items_(const_cast<Data*>(items)), itemcnt_(itemcnt) {
    curpos_ = 0;
  }
  virtual ~Impl1Iter() = default;
public:
  virtual string operator*() final {
    return items_[curpos_]();
  }
  virtual const bool hasNext() final {
    if (curpos_ < itemcnt_) { return true; }
    else { return false; }
  }
  virtual shared_ptr<Data> operator++() final {
    return make_shared<Data>(items_[curpos_++]);
  }
private:
  Data* items_;
  int itemcnt_;
  int curpos_;
};

class Impl2Iter : public Iterator {
public:
  Impl2Iter(list<shared_ptr<Data>>& items) 
  : items_(items), curpos_(items_.begin()) {

  }

public:
  virtual string operator*() final {
    return (*(*curpos_))();
  }
  virtual const bool hasNext() final {
    return (curpos_ != items_.end());
  }
  virtual shared_ptr<Data> operator++() final {
    return *(curpos_++);
  }
  list<shared_ptr<Data>>& items_;
  list<shared_ptr<Data>>::iterator curpos_;
};


class Impl {
public:
  virtual shared_ptr<Iterator> iterator() =0;
};

class Impl1 : public Impl {
public:
  Impl1(const int len = 5) : itemcnt_(len) {
    items_ = new Data[len];
    memset(items_, 0, sizeof(Data)*len);
    items_[0] = Data("1-1");
    items_[1] = Data("1-2");
    items_[2] = Data("1-3");
    items_[3] = Data("1-4");
    items_[4] = Data("1-5");
  }
  virtual ~Impl1() {
    delete[] items_;
  }
public:
  virtual shared_ptr<Iterator> iterator() final {
    return make_shared<Impl1Iter>(items_, itemcnt_);
  }
private:
  Data* items_;
  int itemcnt_;
};

class Impl2 : public Impl {
public:
  Impl2() {
    items_.push_back( make_shared<Data>(Data("2-1")) );
    items_.push_back( make_shared<Data>(Data("2-2")) );
    items_.push_back( make_shared<Data>(Data("2-3")) );
    items_.push_back( make_shared<Data>(Data("2-4")) );
    items_.push_back( make_shared<Data>(Data("2-5")) );
  }
  virtual ~Impl2() = default;
public:
  virtual shared_ptr<Iterator> iterator() final {
    return make_shared<Impl2Iter>(items_);
  }
private:
  list<shared_ptr<Data>> items_;
};


class UserOfImpls {
public:
  UserOfImpls() {
    // impl1_ = make_unique<Impl1>(/*5*/);
    // impl2_ = make_unique<Impl2>();
    impls_.push_back( make_unique<Impl1>(/*5*/) );
    impls_.push_back( make_unique<Impl2>() );
  }
public:
  void readItemsData() {
    // shared_ptr<Iterator> it1 = impl1_->iterator();
    // shared_ptr<Iterator> it2 = impl2_->iterator();

    // readFrom(it1);
    // readFrom(it2);
    for (auto& impl: impls_) {
      readFrom(impl->iterator());
    }
  }
private:
  void readFrom(shared_ptr<Iterator> it) {
    do {
      auto d = (*it).operator++();
      cout << (*d)() << endl;
    } while (it->hasNext());
  }
  
private:
  // unique_ptr<Impl1> impl1_;
  // unique_ptr<Impl2> impl2_;
  list<unique_ptr<Impl>> impls_;
};


void iteratorSample() {
  UserOfImpls user;
  user.readItemsData();
}

}//!namespace iterator_concept {