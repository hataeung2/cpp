/**
 * @file observer.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-07
 * 
 * @copyright Copyright (c) 2023
 * 
 */
#include <set>
#include <memory>
#include <iostream>
using namespace std;
namespace observer {




class Subject {
public:
  class IObserver {
  public:
    IObserver(shared_ptr<Subject> subj) : subj_(subj) { 
      cout << "Subject created" << endl;
    }
    virtual ~IObserver() = default;
  public:
    void notified() {
      pull();
    };
    virtual void display() =0;

  protected:
    virtual void pull() =0;
  protected:
    shared_ptr<Subject> subj_;
  };
public:
  Subject() : data1_("1"), data2_("2") { };
  ~Subject() = default;
public:
  string getData1() const {
    return data1_;
  };
  string getData2() const {
    return data2_;
  };
public:
  void dataChanged() {
    notifyObservers();
  }
private:
  string data1_;
  string data2_;

public:
  void registerObserver(shared_ptr<IObserver> obsvr) {
    observers_.insert(obsvr);
  }
  void removeObserver() { 
    // no impl for shortening code
  }
  void notifyObservers() {
    for (auto obsvr : observers_) {
      obsvr->notified();
    }
  }
private:
  set<shared_ptr<IObserver>> observers_;
};



class Observer1 : public Subject::IObserver {
public:
  Observer1(shared_ptr<Subject> subj) : IObserver(subj) {};
  virtual ~Observer1() = default;
public:
  virtual void display() final {
    cout << "observer1 pulled data: " << disp_data1_ << endl;
  };
private:
  virtual void pull() final {
    disp_data1_ = subj_->getData1();
  }
  string disp_data1_;
};

class Observer2 : public Subject::IObserver {
public:
  Observer2(shared_ptr<Subject> subj) : IObserver(subj) {};
  virtual ~Observer2() = default;
public:
  virtual void display() final {
    cout << "observer2 pulled data: " << disp_data1and2_ << endl;
  };
private:
  virtual void pull() final {
    disp_data1and2_ += subj_->getData1();
    disp_data1and2_ += ", ";
    disp_data1and2_ += subj_->getData2();
  }
  string disp_data1and2_;
};



void observerSample() {
  shared_ptr<Subject> subj{ make_shared<Subject>() } ;
  shared_ptr<Observer1> obsvr1{ make_shared<Observer1>(subj) };
  shared_ptr<Observer2> obsvr2{ make_shared<Observer2>(subj) };

  subj->registerObserver(obsvr1);
  subj->registerObserver(obsvr2);
  subj->notifyObservers();

  /**
   * @brief shortening renderer(display object)
   * 
   */
  set<shared_ptr<Subject::IObserver>> obsvrs;
  obsvrs.insert(obsvr1);
  obsvrs.insert(obsvr2);
  for (auto obsvr : obsvrs) {
    obsvr->display();
  }

}

}//!namespace observer {