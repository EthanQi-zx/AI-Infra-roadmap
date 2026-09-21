# logtool

一个零依赖的 Python 命令行小工具，提供**日志分析统计**与**文件批量处理**两大类能力，单文件、纯标准库实现，开箱即用。

## 功能特性

- **日志级别统计**：一键统计日志文件中各级别（DEBUG / INFO / WARN / ERROR / CRITICAL / FATAL）的分布与总行数
- **错误日志筛选**：精准定位 ERROR / CRITICAL / FATAL 错误日志，附带行号
- **关键字检索**：大小写不敏感的关键字匹配，支持限制输出行数
- **文件批量处理**：递归匹配目录下文件，支持批量重命名、批量修改后缀、批量清理
- **安全预览**：所有文件操作均支持 `--dry-run`，先预览再执行
- **零依赖**：仅使用 Python 标准库（argparse / re / pathlib / collections），无需安装任何第三方包

## 环境要求

- Python 3.6+
- 无需安装任何第三方依赖

## 快速开始

```bash
# 查看帮助
python logtool.py --help

# 统计日志级别分布（以仓库自带的 app.log 为例）
python logtool.py log stats app.log

# 筛选错误日志
python logtool.py log error app.log

# 按关键字匹配日志，最多输出 5 行
python logtool.py log grep app.log -k timeout -n 5
```

## 命令文档

### log — 日志处理

| 命令 | 说明 | 必选参数 | 可选参数 |
| --- | --- | --- | --- |
| `log stats <file>` | 统计日志级别分布与总行数 | `file`：日志文件路径 | — |
| `log error <file>` | 筛选并输出错误级日志（ERROR / CRITICAL / FATAL），带行号 | `file`：日志文件路径 | — |
| `log grep <file> -k <keyword>` | 关键字匹配日志（大小写不敏感），带行号 | `file`：日志文件路径 | `-k/--keyword`：匹配关键字；`-n/--limit`：限制输出行数 |

### file — 文件批量处理

| 命令 | 说明 | 必选参数 | 可选参数 |
| --- | --- | --- | --- |
| `file rename <dir> -r OLD NEW` | 批量重命名：将文件名中的旧字符串替换为新字符串 | `directory`：目录路径；`-r/--replace`：`OLD NEW` 两个值 | `-p/--pattern`：匹配模式（默认 `*`）；`--dry-run`：仅预览 |
| `file ext <dir> -e .log` | 批量修改文件后缀 | `directory`：目录路径；`-e/--ext`：新后缀（如 `.log`） | `-p/--pattern`：匹配模式；`--dry-run`：仅预览 |
| `file clean <dir> -f` | 批量删除文件 | `directory`：目录路径 | `-p/--pattern`：匹配模式；`-f/--force`：真正删除（不加则仅列出待删除项）；`--dry-run`：仅预览 |

> 提示：`file` 系列命令使用递归匹配（`rglob`），`-p` 支持 `*.txt` 这类通配符。**删除类操作请务必先加 `--dry-run` 预览确认。**

## 使用示例

```bash
# 统计日志级别
$ python logtool.py log stats app.log
文件: app.log
总行数: 11
INFO      4
ERROR     2
WARN      2
DEBUG     1
CRITICAL  1
FATAL     1

# 筛选错误日志
$ python logtool.py log error app.log
5: 2026-01-01 10:00:04 ERROR timeout when calling api
6: 2026-01-01 10:00:06 ERROR timeout again
8: 2026-01-01 10:00:07 CRITICAL db connection lost
11: 2026-01-01 10:00:10 FATAL shutting down
总计: 4 条错误日志

# 预览批量重命名（不实际执行）
$ python logtool.py file rename . -r .log .bak -p "*.log" --dry-run
[预览]: app.log -> app.bak
```

## 目录结构

```
python命令行工具/
├── logtool.py    # 主程序（单文件实现）
├── app.log       # 示例日志文件
├── README.md     # 项目说明
├── docs/         # 文档目录
└── logs/         # 日志目录
```

## 设计说明

- **日志级别匹配**：使用正则表达式匹配，大小写不敏感；`WARNING` 与 `WARN` 均归一化为 `WARN`
- **安全机制**：`file clean` 必须显式添加 `-f/--force` 才会真正删除文件，否则仅打印待删除列表；所有文件操作均支持 `--dry-run` 预览
- **退出码**：正常完成返回 0；用户中断（Ctrl+C）返回 130；运行出错返回 1
