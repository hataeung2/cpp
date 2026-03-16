/**
 * @file factory.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-08
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#include <iostream>
#include <memory>
using namespace std;
namespace factory {

enum CarModel {
  eStandard,
  ePerformance,
  eLongRange
};

struct CarSpec {
  CarModel model;
  string options;
};


class CarFunctions {
public:
  void schedule() {
    cout << "the optional functions are operating... " << endl;
    for (auto& f : functions_) {
      cout << f << endl;
    }
  }
  void add(const string& func) {
    functions_.push_back(func);
  }
private:
  vector<string> functions_;
};

class Car {
public:
  Car(const CarSpec spec) : spec_(spec), cf_(make_shared<CarFunctions>()) {
    cout << "car is being created" << endl;
  }
  virtual ~Car() = default;
  shared_ptr<CarFunctions> getCarFunctions() {
    return cf_;
  }
// protected:
  virtual void setCarFunction(const string func) =0;
  virtual void run() =0;
public:
  //...
  const CarSpec getSpec() const { return spec_; }
protected:
  CarSpec spec_;
  shared_ptr<CarFunctions> cf_;
};

class StandardCar : public Car {
public:
  StandardCar(const CarSpec spec) : Car(spec) { 
    cout << "StandardCar is being created" << endl;
  }
public:
  virtual ~StandardCar() = default;
  virtual void setCarFunction(const string func) final {
    cout << "add a car function " << func << " into StandardCar" << endl;
    cf_->add(func);
  }
  virtual void run() final {
    cout << "StandardCar is running" << endl;
    cf_->schedule();
  }
};
class PerformanceCar : public Car {
public:
  PerformanceCar(const CarSpec spec) : Car(spec) { 
    cout << "PerformanceCar is being created" << endl;
  }
public:
  virtual ~PerformanceCar() = default;
  virtual void setCarFunction(const string func) final {
    cout << "add a car function " << func << " into PerformanceCar" << endl;
    cf_->add(func);
  }
  virtual void run() final {
    cout << "PerformanceCar is running" << endl;
    cf_->schedule();
  }
};
class LongRangeCar : public Car {
public:
  LongRangeCar(const CarSpec spec) : Car(spec) { 
    cout << "LongRangeCar is being created" << endl;
  }
public:
  virtual ~LongRangeCar() = default;
  virtual void setCarFunction(const string func) final {
    cout << "add a car function " << func << " into LongRangeCar" << endl;
    cf_->add(func);
  }
  virtual void run() final {
    cout << "LongRangeCar is running" << endl;
    cf_->schedule();
  }
};





class ACarFactory {
public:
  virtual shared_ptr<Car> make(const CarSpec& spec) =0;

public:
  static std::vector<string> sliceOptionFromOrder(const string& options) {
    std::vector<std::string> tokens;

    size_t start = 0;
    size_t commaPos = options.find(',');

    while (commaPos != std::string::npos) {
        tokens.push_back(options.substr(start, commaPos - start));
        start = commaPos + 1;
        commaPos = options.find(',', start);
    }
    return tokens;
  }
};

class CarFactoryKorea : public ACarFactory {
public:
  virtual shared_ptr<Car> make(const CarSpec& spec) {
    unique_ptr<Car> car = [&]() -> unique_ptr<Car> {
      switch (spec.model) {
        case CarModel::eStandard:
          return make_unique<StandardCar>(spec);
        case CarModel::ePerformance:
          return make_unique<PerformanceCar>(spec);
        default:
          return nullptr;
      }
    }();
    if (car) {
      auto options{ sliceOptionFromOrder(spec.options) };
      for (const auto& o : options) {
        car->setCarFunction(o);
      }
      return car;
    } else {
      throw runtime_error("no car created");
    }
  }
};

class CarFactoryTexas : public ACarFactory {
public:
  virtual shared_ptr<Car> make(const CarSpec& spec) {
    unique_ptr<Car> car;
    switch (spec.model) {
      case CarModel::eLongRange:
        car = make_unique<LongRangeCar>(spec);
        break;
    }
    if (car) {
      auto options{ sliceOptionFromOrder(spec.options) };
      for (const auto& o : options) {
        car->setCarFunction(o);
      }
      return car;
    } else {
      throw runtime_error("no car created");
    }
    
  }
};






class CarSeller {
public:
  virtual const CarSpec consult(const string customer_requirement) =0;
  virtual shared_ptr<Car> sellCar(const CarSpec& spec) =0;
private:
  virtual shared_ptr<Car> orderCarFromFactory(const CarSpec& spec) =0;
};

class GoodCarSeller : public CarSeller {
public:
  virtual const CarSpec consult(const string customer_requirement) {
    cout << "check availability, leadtime from factories" << endl;
    cout << "find out the best way to get the car" << endl;
    CarModel model{ CarModel::eStandard };
    // model
    if (std::string::npos != customer_requirement.find("fast")) {
      model = CarModel::ePerformance;
    } else if (std::string::npos != customer_requirement.find("economic")) {
      model = CarModel::eLongRange;
    }
    // options
    string options{};
    if (std::string::npos != customer_requirement.find("FullSelfDriving")) { 
      options += "FSD,";
    } if (std::string::npos != customer_requirement.find("SafetyStop")) {
      options += "SAFESTOP,";
    }// ...    
    CarSpec spec;
    spec.model = model;
    spec.options = options;
    return spec;
  }
  virtual shared_ptr<Car> sellCar(const CarSpec& spec) {
    // make contract, down payment, ...
    cout << "make contract with down payment, monthly installment with low interest" << endl;
    return orderCarFromFactory(spec);
  }
private:
  virtual shared_ptr<Car> orderCarFromFactory(const CarSpec& spec) {
    shared_ptr<ACarFactory> factory = [&]() -> shared_ptr<ACarFactory> {
      switch (spec.model)
      {
      case CarModel::eStandard:
      case CarModel::ePerformance:
        return std::make_shared<CarFactoryKorea>();
      case CarModel::eLongRange:
        return std::make_shared<CarFactoryTexas>();
      default:
        return nullptr;
      }
    }();
    if (factory) {
      return factory->make(spec);
    } else {
      throw runtime_error("no factory created");
    }
    
  }
};

class BadCarSeller : public CarSeller {
public:
  virtual const CarSpec consult(const string customer_requirement) {
    cout << "suggest the one the seller want to sell. no option added even though the customer asked." << endl;
    CarSpec spec;
    spec.model = CarModel::eStandard;
    spec.options = "";
    return spec;
  }
  virtual shared_ptr<Car> sellCar(const CarSpec& spec) {
    cout << "make contract with no down payment, monthly installment with high interest" << endl;
    return orderCarFromFactory(spec);
  }
private:
  virtual shared_ptr<Car> orderCarFromFactory(const CarSpec& spec) {
    shared_ptr<ACarFactory> factory{ make_shared<CarFactoryKorea>() };
    return factory->make(spec);
  }
};

class Customer {
public:
  static void buyCarFromGoodSeller() {
    cout << ">> Customer meets the Good Seller" << endl;
    GoodCarSeller gcs;
    auto carSpec = gcs.consult("fastest car ever, FullSelfDriving, SafetyStop");
    auto car = gcs.sellCar(carSpec);
    
    cout << "test car" << endl;
    car->run();
    cout << ">> Customer satisfied" << endl;
  }
  static void buyCarFromBadSeller() {
    cout << ">> Customer meets the Bad Seller" << endl;
    BadCarSeller bcs;
    auto carSpec = bcs.consult("fastest car ever, FullSelfDriving");
    auto car = bcs.sellCar(carSpec);

    cout << "test car" << endl;
    car->run();
    cout << ">> Customer angry" << endl;
  }
};



void factorySample() {
  // customers don't know what is going to be done from car seller and company(factory)
  //  customers just choose the seller to buy a car.

  // carseller don't know what is going to be done from factory. 
  //  carseller just choose the factory to order.

  Customer::buyCarFromBadSeller();
  Customer::buyCarFromGoodSeller();
}

}//!namespace factory {