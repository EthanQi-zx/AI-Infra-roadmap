#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <atomic>
#include <future>
#include <memory>
#include <stdexcept>
#include <iostream>
using namespace std;

// 线程池类
class ThreadPool {
public:
    // explicit表示构造函数不能被隐式调用，必须显式调用
    explicit ThreadPool(size_t threads);
    ~ThreadPool();
    // =delete是C++11的语法，表示显示删除函数
    ThreadPool(const ThreadPool&) = delete; //删除拷贝构造函数
    ThreadPool& operator=(const ThreadPool&) = delete; //删除拷贝赋值运算符

    template<typename F, typename... Args>
    auto enqueue(F&& f, Args&&... args)-> future<typename result_of<F(Args...)>::type>; //任务入队函数 

private:
    void worker_loop(); //工作线程循环函数
    vector<thread> workers_; //工作线程容器
    queue<function<void()>> tasks_; //任务队列
    mutex queue_mutex_; //互斥锁
    condition_variable condition_; //条件变量
    atomic<bool> stop_{false}; //停止标志，默认值为false
};

// 构造函数，创建完线程池后，线程池中的线程会立即开始执行worker_loop函数，等待任务的到来
ThreadPool::ThreadPool(size_t threads) {
    for(size_t i = 0; i < threads; ++i) {
        workers_.emplace_back([this]{worker_loop();});
    }
}

// 工作线程循环函数，线程池中的每个线程都会执行这个函数，等待任务的到来
void ThreadPool::worker_loop() {
    for(;;) {   // 线程循环，等待任务的到来
        function<void()> task;
        {
            // 加锁，独占队列，如果当前没有锁，就把当前线程挂起等待，不占用CPU资源，直到获取到锁为止
            unique_lock<mutex> lock(queue_mutex_);

            // 队列空则释放锁并休眠，等待条件变量唤醒再重新获得锁
            //只要wait的第二个参数返回false，就会一直阻塞等待，直到条件变量被唤醒，返回true才会继续执行
            // tasks为空时，!tasks_.empty()为false，则处于wait阻塞状态休眠
            condition_.wait(lock, [this] {
                return stop_.load() || !tasks_.empty();
            }); 

            if(stop_.load() && tasks_.empty()) {
                break; // 如果线程池停止且任务队列为空，则退出循环
            }

            // 如果任务队列不为空，就取队头任务
            task = move(tasks_.front()); // 获取任务队列的第一个任务
            tasks_.pop(); // 弹出任务队列的第一个任务
        }   //出了作用域之后自动解锁
        // 取任务的时候上锁，执行的时候不上锁，防止任务执行时间过长，阻塞其他线程获取任务
        task(); // 执行任务
    }
}

// 任务入队函数：投递任务 + 通知一个线程
template<typename F, typename... Args>
auto ThreadPool::enqueue(F&& f, Args&&... args)->future<typename result_of<F(Args...)>::type>
{
    using ret_type = typename result_of<F(Args...)>::type; // 获取函数返回值类型
    // 把f(args...)包装成packaged_task，执行时结果自动存入future
    auto task = make_shared<packaged_task<ret_type()>>(bind(forward<F>(f), forward<Args>(args)...));    

    future<ret_type> res = task->get_future(); // 获取future对象，用于获取任务执行结果

    {
        lock_guard<mutex> lock(queue_mutex_);
        // 如果线程池已经停止，则抛出异常
        if(stop_.load()) {
            throw runtime_error("enqueue on stopped ThreadPool");
        }
        tasks_.emplace([task]() {(*task)();}); // 将任务加入任务队列
    }
    // 唤醒放在锁外，防止唤醒其他锁之后仍需要获取锁，导致其他线程阻塞
    condition_.notify_one(); // 通知一个线程去执行任务

    return res; // 返回future对象
}

// 析构函数，停止线程池，等待所有线程退出
ThreadPool::~ThreadPool() {
    stop_.store(true); // 设置停止标志
    condition_.notify_all(); // 唤醒所有线程，让他们看到stop_并退出循环
    for(thread& worker: workers_) {
        // 主线程等在这，等待子线程真正结束再退出，防止子线程还在执行任务，导致程序异常退出
        worker.join();
    }
}

int main() {
    int completed = 0;    //记录完成的任务数
    mutex io_mtx;

    {
        ThreadPool pool(4); // 创建一个线程池，包含4个线程

        // 测试1：投递一批带返回值的任务
        vector<future<int>> futures;
        for(int i = 0; i < 8; ++i) {
            futures.emplace_back(pool.enqueue([i] {
                return i * i;
            }));
        }
        for(auto& f: futures) {
            cout << f.get() << " "; // 获取任务执行结果
        }
        cout << endl;

        // 测试 2：验证线程复用 —— 看每个任务落在哪个线程上
        for(int i = 0; i < 8; ++i) {
            pool.enqueue([&io_mtx, i] {
                lock_guard<mutex> lock(io_mtx);
                cout << "Task " << i << " is running in thread " << this_thread::get_id() << endl;
            });
        }

        // 测试 3：一批 void 任务，计数
        for(int i = 0; i < 88; ++i) {
            pool.enqueue([&completed, &io_mtx] {
                lock_guard<mutex> lock(io_mtx);
                ++completed;
            });
        }
    }   // <-- 出作用域：ThreadPool 析构，join 所有线程，剩余任务全部执行完
    
    cout << "Completed tasks: " << completed << endl; // 输出完成的任务数
    return 0;
}