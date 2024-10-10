/**
 * @file hardware_interfacing_system.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-15
 * 
 * @copyright Copyright (c) 2023
 * 
 */
#include <iostream>
#include <vector>
#include <list>
#include <map>
#include <memory>
using namespace std;

namespace gs {
using SystemId = unsigned;
using JobId = unsigned;

enum State {
  eUnknown,
  eIdle,
  eBusy,
  eHang,
  eError,
  eStateCnt
};


class SystemSyncService {
public:
  static const bool isOkayToExecute(const ISystem& sys) {
    auto systemtype{ typeid(sys).name() };
  }
  static const list<shared_ptr<ISystem>>& getBusySystems() {

  }
private:
  static list<shared_ptr<ISystem>> registered_systems_;
};


class Command {
public:
  Command() : done_(false) {}
  virtual ~Command() = default;
public:
  virtual void execute() =0;
  virtual void isDone() =0;
protected:
  bool done_;
};

/**
 * @brief One Job is a list of Commands
 * The Commands are listed sequencially in the container
 * 
 */
class Job {
public:
  Job() : curcmdinaction_(nullptr) {}
  ~Job() = default;
public:
  const bool hang() {
    
  }
  const bool hasNext() {
    commands_.size();
  }
public:
  list<shared_ptr<Command>> commands_;
  shared_ptr<Command> curcmdinaction_;
};



class ISystem {
public:
  ISystem() = default;
  virtual ~ISystem() = default;
public:
  virtual void reset() =0;
  virtual void initialize() =0;
  virtual void schedule() =0;
public:
  virtual void operate(const Command& cmd) =0;
public:
  virtual const State getState() =0;
private:
  virtual void setState(const State state) =0;
};

class SubSystem1 : public ISystem {
  friend class Scheduler;
public: // commands for SubSystem1
  class Open : public Command {
  public:
    Open(SubSystem1& system) : system_(system) {

    };
    virtual ~Open() = default;
  public:
    virtual void execute() {
      cout << "cmd: SubSystem1 Open" << endl;
    }
  private:
    SubSystem1& system_;
  };
  class Close : public Command {
  public:
    Close() = default;
    virtual ~Close() = default;
  public:
    virtual void execute() {
      cout << "cmd: SubSystem1 Close" << endl;
    }
  };
private:
  SubSystem1() = default;
  virtual ~SubSystem1() = default;
public:
  virtual void operate(const Command& cmd) final {
    // get the condition to perform the cmd
    // if it is okay to proceed, then execute it.
    // check the other subsystems condition
    const_cast<Command&>(cmd).execute();
  }
private:
  // some hardware interface api wrapper

};

class SubSystem2 : public ISystem {
  friend class Scheduler;
public: // commands for SubSystem1
  class GetMaterial : public Command {
  public:
    GetMaterial() = default;
    virtual ~GetMaterial() = default;
  public:
    virtual void execute() {
      cout << "cmd: SubSystem2 GetMaterial" << endl;
    }
  };
  class PutMaterial : public Command {
  public:
    PutMaterial() = default;
    virtual ~PutMaterial() = default;
  public:
    virtual void execute() {
      cout << "cmd: SubSystem2 PutMaterial" << endl;
    }
  };
private:
  SubSystem2() = default;
  virtual ~SubSystem2() = default;
};

class MainScheduler : public ISystem {
public:
  MainScheduler() = default;
  virtual ~MainScheduler() = default;
public:
  virtual void reset() final {
    // reset every subsystem
    cout << "Reset the subsystems in an organized manner." << endl;
  }
  virtual void initialize() final {
    // initialize subsystems
    cout << "Initiate the subsystems in an organized manner for a smooth startup." << endl;
  }
  virtual void schedule() final {
    for (auto& ss: subsystems_) {
      ss.second->schedule();
    }
  }
public:
  virtual void operate(const Command& cmd) final {
    // nothing
  }
private:
  map<SystemId, shared_ptr<ISystem>> subsystems_;
  map<JobId, shared_ptr<Job>> jobs_;
};



void hardwareInterfacingSample() {
  shared_ptr<Command> cmdS1Open = make_shared<SubSystem1::Open>();
  shared_ptr<Command> cmdS1Close = make_shared<SubSystem1::Close>();

  MainScheduler ms;
  ms.initialize();
  ms.schedule();
  ms.operate((*cmdS1Open));
  // init 
  // idle
  // make a job 1-1
  // standby
  // make a job 1-2
  // standby
  // make a job 2
  // standby
  // make a job 3
  // run the jobs - busy
  //  - same kind of jobs are te be done sequentially
  //  - different kind of jobs are to be done parallelly but some conditions should be blocked to prevent hw collision
  // busy
  // make a job 4 - busy
  //  - adding another job is possible
  // jobs done - idle

  // make another job
  // hang while running the job
  // undo a command that was done most recently
  // undo all the commands to cancel the job


}



}//!namespace gs {