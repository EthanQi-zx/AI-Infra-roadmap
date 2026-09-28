# ThreadPool · 基于 C++11 的通用线程池

一个轻量、可直接编译运行的 **C++11 线程池**，采用「任务队列 + 工作线程 + 互斥锁 + 条件变量」经典模型。线程只创建一次、反复复用，用于高效执行高频短小的并发任务。

## 特性

- ✅ **线程复用**：固定数量的工作线程常驻，反复从队列取任务执行，避免频繁创建/销毁线程的开销
- ✅ **获取返回值**：`enqueue` 返回 `std::future`，可阻塞等待并取回任务结果或捕获任务内异常
- ✅ **优雅关闭**：析构时置停止标志、唤醒所有线程、`join` 等待，队列中剩余任务会被完整执行完，不丢任务
- ✅ **虚假唤醒安全**：条件变量使用带谓词的 `wait`，重查条件，杜绝虚假唤醒
- ✅ **线程安全**：队列所有访问均在互斥锁保护下，任务在锁外执行，避免死锁与数据竞争
- ✅ **C++11 标准**：无第三方依赖，单文件即用，兼容 C++14/17
- ✅ **防误用**：禁用拷贝/赋值，停止后 `enqueue` 抛异常拒绝

## 工作原理

```
                ┌──────────────────────────────────────────┐
   调用方 enqueue│  任务队列 tasks_  (std::queue)             │
   ────────────▶│  互斥锁 queue_mutex_ 保护队列               │
                │  条件变量 condition_ 休眠/唤醒空闲线程       │
                │  工作线程 workers_  (常驻，循环取任务执行)    │
                │  停止标志 stop_ (atomic) 优雅关闭           │
                └──────────────────────────────────────────┘
```

- **生产-消费模型**：调用方（生产者）把任务压入队列；工作线程（消费者）循环取任务执行。
- **条件变量**：队列为空时空闲线程阻塞休眠、不占 CPU；有新任务时 `notify_one` 唤醒一个线程。
- **锁内取/放，锁外执行**：共享数据只有队列，故仅对「取放任务」加锁，任务本体的执行放在锁外，保证并行度并规避死锁。
- **优雅关闭**：析构时 `stop_ = true` → `notify_all` 唤醒全部线程 → 线程发现「已停止且队列为空」后退出 → 逐个 `join` 回收。

## 快速开始

### 环境要求

- 支持 C++11 及以上的编译器（GCC / Clang / MSVC）
- 无第三方依赖，仅需标准库

### 编译运行

**Linux / macOS（g++ 或 clang++）**

```bash
g++ -std=c++11 -pthread -O2 ThreadPool.cpp -o threadpool
./threadpool
```

**Windows（MinGW g++）**

```bat
g++ -std=c++11 -pthread -O2 ThreadPool.cpp -o ThreadPool.exe
ThreadPool.exe
```

**Windows（MSVC / Visual Studio 开发者命令行）**

```bat
cl /EHsc /std:c++14 ThreadPool.cpp
ThreadPool.exe
```

> 注意：Linux/macOS 必须带 `-pthread`，MSVC 必须带 `/EHsc`（启用 C++ 异常支持），否则可能编译失败或运行崩溃。

### 预期输出

```
0 1 4 9 16 25 36 49
Task 1 is running in thread 0xc8
Task 0 is running in thread 0xcc
Task 3 is running in thread 0xcc
...
Completed tasks: 88
```

- 前 8 个数为 `i*i` 的返回值（`i = 0..7`）。
- 任务运行线程的 ID 种类不超过线程数（此处为 4），说明**线程被复用**。
- 最后一行 `Completed tasks: 88` 表示 88 个任务全部执行完成，无丢失。

## 使用示例

### 1. 投递带返回值的任务

```cpp
ThreadPool pool(4);

std::future<int> f = pool.enqueue([] { return 42; });
std::cout << f.get() << std::endl;   // 42
```

### 2. 投递带参数的任务

```cpp
ThreadPool pool(4);

pool.enqueue([](int a, int b) {
    std::cout << a + b << std::endl;  // 3
}, 1, 2);
```

### 3. 投递 void 任务

```cpp
ThreadPool pool(4);

int count = 0;
std::mutex mtx;
for (int i = 0; i < 100; ++i) {
    pool.enqueue([&] {
        std::lock_guard<std::mutex> lk(mtx);
        ++count;
    });
}
// pool 析构时会 join 所有线程，等待全部任务执行完毕
```

### 4. 捕获任务内异常

```cpp
ThreadPool pool(4);

auto f = pool.enqueue([]() -> int { throw std::runtime_error("boom"); return 1; });
try {
    f.get();
} catch (const std::exception& e) {
    std::cout << e.what() << std::endl;   // boom
}
```

## API 说明

| 接口 | 说明 |
|------|------|
| `explicit ThreadPool(size_t threads)` | 构造线程池并启动 `threads` 个工作线程 |
| `~ThreadPool()` | 析构：优雅关闭，`join` 所有线程，等待队列任务执行完毕 |
| `template<F, Args...> auto enqueue(F&& f, Args&&... args) -> std::future<...>` | 投递任务，返回 `std::future` 以获取返回值/异常；线程池已停止时抛 `std::runtime_error` |
| 拷贝构造 / 拷贝赋值 | 已 `= delete` 禁用，线程池不可复制 |

## 项目结构

```
.
├── ThreadPool.cpp      # 线程池实现 + 测试程序（单文件，可直接编译运行）
└── README.md           # 本文档
```

## 进阶方向

- 支持任务优先级：将 `std::queue` 换为 `std::priority_queue`，按优先级出队
- 动态扩缩容：繁忙时增加线程、空闲时回收
- 任务取消 / 超时：结合 `std::future::wait_for`
- 无锁队列优化：降低锁竞争

## License

[MIT](LICENSE)（如未添加 LICENSE 文件，请按需选择开源协议并补充）

---

欢迎 Star / Fork / Issue。如果对你有帮助，也欢迎在你的项目中直接复用 `ThreadPool.cpp`。
