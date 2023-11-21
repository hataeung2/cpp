///
// condition variable usage
///

#include <queue>
#include <mutex>
#include <thread>
#include <string>
#include <condition_variable>

static std::queue<std::string> q_;
static std::mutex door_;
static std::condition_variable cv_;
void condition_variable_usage1() {
  std::cout << __func__ << "start" << std::endl;


  ///
  // thread1 - working the other job with q_
  ///
  bool _continue{ true };
  auto t1 = std::thread([&_continue]{
    q_.push("elem1");
    q_.push("elem2");
    q_.push("elem3");
    q_.push("elem4");
    q_.push("elem5");
    while (_continue) {
      std::this_thread::sleep_for(std::chrono::seconds(1));
      {
        std::lock_guard lock(door_); // NOW LOCK
        if (0 == q_.size()) {
          _continue = false;
          break;
        }
        q_.pop();
        std::cout << "elem poped from q_. elem cnt: " << q_.size() << std::endl;
      }
      std::cout << "about to notify cv_'s owner thread(main) to wake up" << std::endl;
      cv_.notify_all();
    } 
  });




  ///
  // main thread logic - working with jobs including q_
  ///
  auto main_t = std::thread([&] {
    ///
    // NOW LOCK 'door_' creating
    ///
    std::unique_lock lock(door_);
    ///
    // LOCKed
    ///

    // std::cout 
    //   << "about to sleep this thread(main), \n 
    //   'door_' UNLOCKed so that the other threads can access to 'door_'. \n 
    //   when 'notify_one' or 'notify_all' called, this thread(main) is to wake up and \n
    //   do the condition check by the lambda function of '[&]{ return !q_.empty(); }'. \n
    //   if the lambda function returns true then the condition satisfied so escape 'wait' condition with lock the 'door_'.\n
    //   at this moment, the other threads(using 'door_' mutex) wait until 'door_' UNLOCKed again. \n
    //   " << std::endl;
    cv_.wait(lock, [&]{ return 2 >= q_.size(); }); // NOW UNLOCK when calling 'wait'
    ///
    // now LOCKed. so can do something sync 
    ///
    std::this_thread::sleep_for(std::chrono::seconds(1));
  
  });


  // wait for threads to end
  t1.join();
  main_t.join();
  std::cout << __func__ << "end" << std::endl;
}

