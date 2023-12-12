/**
 * @file command.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-11
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#include <iostream>
#include <memory>
#include <list>
#include <map>
#include <vector>
using namespace std;
namespace command {


class Receiver {
public:
  Receiver() = default;
  virtual ~Receiver() = default;
};

class Light : public Receiver {
public:
  Light() = default;
  virtual ~Light() = default;
public:
  virtual void on() {
    cout << "Light ON" << endl;
  }
  virtual void off() {
    cout << "Light OFF" << endl;
  }

};

class TheOtherCompanyLight : public Light {
public:
  TheOtherCompanyLight() = default;
  virtual ~TheOtherCompanyLight() = default;
public:
  virtual void on() final {
    cout << "call TheOtherCompanyLightApi to turn ON the light" << endl;
    other_light_.on();
  }
  virtual void off() final {
    cout << "call TheOtherCompanyLightApi to turn OFF the light" << endl;
    other_light_.off();
  }
private:
  // for conceptual explanation. 
  // it should be capsulated by the other company. we don't know the concrete implimentation
  class TheOtherCompanyLightApi {
  public:
    TheOtherCompanyLightApi() = default;
    ~TheOtherCompanyLightApi() = default;
  public:
    void on() {
      cout << "the other company light ON" << endl;
    }
    void off() {
      cout << "the other company light OFF" << endl;
    }
    void dim() {
      cout << "the other company light DIMMED" << endl;
    }
  };
  TheOtherCompanyLightApi other_light_;
};


class Command {
public:
  Command() = default;
  virtual ~Command() = default;
public:
  virtual void execute() =0;
};

class LightOnCommand : public Command {
public:
  LightOnCommand(shared_ptr<Light> recvr) {
    receivers_.push_back(recvr);
  }
  virtual void execute() final {
    for (auto& r: receivers_) {
      r->on();
    }
  }
private:
  list<shared_ptr<Light>> receivers_;
};

class LightOffCommand : public Command {
public:
  LightOffCommand(shared_ptr<Light> recvr) {
    receivers_.push_back(recvr);
  }
  virtual void execute() final {
    for (auto& r: receivers_) {
      r->off();
    }
  }
private:
  list<shared_ptr<Light>> receivers_;
};



class Client {
using InvokerId = int;
public:
  Client() = default;
  ~Client() = default;
public:
  void progamSetup() {
    auto light = make_shared<Light>();
    auto lightOnCommand = make_shared<LightOnCommand>(light);
    auto lightOffCommand = make_shared<LightOffCommand>(light);

    invokers_.insert(make_pair(1, make_shared<Invoker>(lightOnCommand)));
    invokers_.insert(make_pair(2, make_shared<Invoker>(lightOffCommand)));

    auto otherLight = make_shared<TheOtherCompanyLight>();
    auto otherLightOnCommand = make_shared<LightOnCommand>(otherLight);
    auto otherLightOffCommand = make_shared<LightOffCommand>(otherLight);

    invokers_.insert(make_pair(3, make_shared<Invoker>(otherLightOnCommand)));
    invokers_.insert(make_pair(4, make_shared<Invoker>(otherLightOffCommand)));
  }
public:
  void operateSwitch(const InvokerId iid) {
    (*invokers_[iid])();
  }

private:
  class Invoker {
  public:
    Invoker(shared_ptr<Command> cmd) {
      setCommand(cmd);
    }
    ~Invoker() = default;
    void setCommand(shared_ptr<Command> cmd) {
      commands_.push_back(cmd);
    }
    void operator()() {
      for (auto& c : commands_) {
        c->execute();
      }
    }
  private:
    vector<shared_ptr<Command>> commands_;
  };

private:
  map<InvokerId, shared_ptr<Invoker>> invokers_;
};

void commandSample() {
  Client client;
  client.progamSetup();

  client.operateSwitch(1);
  client.operateSwitch(2);
  client.operateSwitch(3);
  client.operateSwitch(4);
}

}//!namespace command {