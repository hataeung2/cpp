/**
 * @file state.hpp
 * @author Taeung Ha (aha3546@outlook.com)
 * @brief 
 * @version 0.1
 * @date 2023-12-05
 * 
 * @copyright Copyright (c) 2023
 * 
 */
#include <iostream>
#include <memory>
using namespace std;
namespace astate {

// for example, there can be some states like below.
enum MachineStateId {
  eEmergencyStop,
  eIdle,
  eStandBy,
  eRun,
  eAbort
};

class Machine;

class IMachineState {
public:
  IMachineState() = default;
  ~IMachineState() {
    cout << "state destroy" << endl;
  }
public:
  virtual const bool isAvailableToTransferTo(const MachineStateId& sid) =0;
  virtual void schedule(const Machine& m) =0;
};

class MachineStateIdle : public IMachineState {
public:
  MachineStateIdle() = default;
  virtual ~MachineStateIdle() {
    cout << "idle state destroy" << endl;
  }
  static std::shared_ptr<MachineStateIdle> getInst() {
    if (nullptr == inst_) {
      inst_ = std::make_shared<MachineStateIdle>();
    } return inst_;
  }
public:
  virtual const bool isAvailableToTransferTo(const MachineStateId& sid) final {
    auto trans_avail = false;
    switch (sid) {
      case MachineStateId::eEmergencyStop:
        // do this immediately
        trans_avail = true;
        break;
      case MachineStateId::eIdle:
        // no transition
        trans_avail = false;
        break;
      case MachineStateId::eStandBy:
        // can transfer
        trans_avail = true;
        break;
      case MachineStateId::eRun:
        // impossible. no transition
        trans_avail = false;
        break;
      case MachineStateId::eAbort:
        // not available. no transition
        trans_avail = false;
        break;
      default:
        cout << "unknown state id received. no state transition." << endl;
        trans_avail = false;
        break;
    }
    return trans_avail;
  }
  virtual void schedule(const Machine& m) final {
    cout << "idle. only update system I/Os." << endl;
  }
private:
  static std::shared_ptr<MachineStateIdle> inst_;
};
std::shared_ptr<MachineStateIdle> MachineStateIdle::inst_;

class MachineStateStandby : public IMachineState {
public:
  MachineStateStandby() = default;
  virtual ~MachineStateStandby() {
    cout << "standby state destroy" << endl;
  }
  static std::shared_ptr<MachineStateStandby> getInst() {
    if (nullptr == inst_) {
      inst_ = std::make_shared<MachineStateStandby>();
    } return inst_;
  }
public:
  virtual const bool isAvailableToTransferTo(const MachineStateId& sid) final {
    auto trans_avail = false;
    switch (sid) {
      case MachineStateId::eEmergencyStop:
        // do this immediately
        trans_avail = true;
        break;
      case MachineStateId::eIdle:
        // not available. no transition
        trans_avail = false;
        break;
      case MachineStateId::eStandBy:
        // no transition
        trans_avail = false;
        break;
      case MachineStateId::eRun:
        // can transfer
        trans_avail = true;
        break;
      case MachineStateId::eAbort:
        // can transfer
        trans_avail = true;
        break;
      default:
        cout << "unknown state id received. no state transition." << endl;
        trans_avail = false;
        break;
    }
    return trans_avail;
  }
  virtual void schedule(const Machine& m) final {
    cout << "standby. ready to operate." << endl;
  }
private:
  static std::shared_ptr<MachineStateStandby> inst_;
};
std::shared_ptr<MachineStateStandby> MachineStateStandby::inst_;

class Machine {
public:
  Machine() : mstat_(MachineStateIdle::getInst()), cur_sid_(MachineStateId::eIdle) { };
  virtual ~Machine() = default;

public:
  void changeState(const MachineStateId& sid) {
    if (isAvailableToTransferTo(sid)) {
      setState(sid);
    } else {
      cout << "- no state transition made." << endl;
    }
  }
  const bool isAvailableToTransferTo(const MachineStateId& sid) {
    return mstat_->isAvailableToTransferTo(sid);
  }
  void schedule() {
    if (nullptr != mstat_.get()) { 
      mstat_->schedule(*this); 
    }
  }
private:
  void setState(const MachineStateId& sid) {
    std::shared_ptr<IMachineState> stat;
    switch (sid) {
      case MachineStateId::eEmergencyStop:
        break;
      case MachineStateId::eIdle:
        stat = MachineStateIdle::getInst();
        break;
      case MachineStateId::eStandBy:
        stat = MachineStateStandby::getInst();
      case MachineStateId::eRun:
        break;
      case MachineStateId::eAbort:
        break;
      default:
        break;
    }

    cout << "- state transition from " << typeid(*mstat_.get()).name();
    mstat_ = stat;
    cout << " to " << typeid(*stat.get()).name() << endl;
  }
  std::shared_ptr<IMachineState> mstat_;
  MachineStateId cur_sid_;
};


void stateChangeSample() {
  auto statIdle{ MachineStateIdle::getInst() };
  auto statStandby{ MachineStateStandby::getInst() };
  // emergency stop, run, abort - no impl for efficiency
  
  Machine m;

  m.changeState(MachineStateId::eStandBy);
  m.schedule();

  m.changeState(MachineStateId::eIdle);
  m.schedule();
}

}//!namespace astate {