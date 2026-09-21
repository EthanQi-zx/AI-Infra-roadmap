import argparse
import re
import sys
from pathlib import Path
from collections import Counter

LEVEL_PATTERN = re.compile(
    r"\b(DEBUG|INFO|WARN(?:ING)?)|ERROR|CRITICAL|FATAL\b",  #\b表示单词边界，匹配日志级别
    re.IGNORECASE   # 忽略大小写匹配
)

# 读取文件内容，逐行返回
def read_lines(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line.strip("\n")

# 统计日志级别，传入的是命令行参数，就是文件路径
def cmd_log_stats(args):
    counter = Counter()
    total = 0

    for line in read_lines(args.file):
        total += 1
        m = LEVEL_PATTERN.search(line)
        if m:
            level = m.group(0).upper()
            if level.startswith("WARN"):
                level = "WARN"
            counter[level] += 1

    print(f"文件: {args.file}")
    print(f"总行数: {total}")
    # 按计数高低返回(level, count)列表
    for level, count in counter.most_common():
        print(f"{level:<10} {count}")

# 记录错误日志
def cmd_log_error(args):
    found = 0
    for i, line in enumerate(read_lines(args.file), 1):
        m = LEVEL_PATTERN.search(line)
        if m and m.group(0).upper() in ("ERROR", "CRITICAL", "FATAL"):
            found += 1
            print(f"{i}: {line}")
    print(f"总计: {found} 条错误日志")

# 记录匹配日志
def cmd_log_grep(args):
    keyword = args.keyword.lower()
    count = 0
    for i, line in enumerate(read_lines(args.file), 1):
        if keyword in line.lower():
            count += 1
            print(f"{i}: {line}")
            if args.limit and count >= args.limit:
                break
    print(f"总计: {count} 条匹配日志")

# 按通配符寻找目录下的文件，返回Path对象列表
def iter_files(directory, pattern):
    base = Path(directory)
    if not base.is_dir():
        print(f"{directory} 不是一个有效的目录", file=sys.stderr)
        sys.exit(1)
    return [p for p in base.rglob(pattern) if p.is_file()]

# 批量重命名文件
def cmd_file_rename(args):
    files = iter_files(args.directory, args.pattern)
    for p in files:
        if args.old not in p.name:
            continue
        new_name = p.name.replace(args.old, args.new)
        new_path = p.with_name(new_name)
        if args.dry_run:
            print(f"[预览]: {p.name} -> {new_name}")
        else:
            p.rename(new_path)
            print(f"[重命名]: {p.name} -> {new_name}")

# 批量修改文件后缀
def cmd_file_ext(args):
    files = iter_files(args.directory, args.pattern)
    new_ext = args.ext if args.ext.startswith(".") else f".{args.ext}"
    for p in files:
        new_path = p.with_suffix(new_ext)
        if args.dry_run:
            print(f"[预览]: {p.name} -> {new_path.name}")
        else:
            p.rename(new_path)
            print(f"[改后缀]: {p.name} -> {new_path.name}")

# 批量删除文件
def cmd_file_clean(args):
    files = iter_files(args.directory, args.pattern)
    for p in files:
        if args.force and not args.dry_run:
            try:
                p.unlink()
                print(f"[删除]: {p}")
            except OSError as e:
                print(f"[错误]: 无法删除 {p}: {e}", file=sys.stderr)
        else: 
            print(f"[待删除]: {p}")

def build_parser():
    # 创建命令行解析器
    parser = argparse.ArgumentParser(description="logtool小工具")
    # 创建子命令解析器
    sub = parser.add_subparsers(dest="command", required=True)


    # 创建log子命令解析器
    log_p = sub.add_parser("log", help="日志处理")
    # 创建log子命令的子命令解析器
    log_sub = log_p.add_subparsers(dest="action", required=True)

    # 创建log stats子命令解析器
    p_stats = log_sub.add_parser("stats", help="统计日志级别")
    # 添加参数，指定日志文件路径
    p_stats.add_argument("file", help="日志文件路径")
    # 设置默认函数，当执行log stats命令时，调用cmd_log_stats函数
    p_stats.set_defaults(func=cmd_log_stats)

    # 创建log error子命令解析器
    p_error = log_sub.add_parser("error", help="记录错误日志")
    p_error.add_argument("file", help="日志文件路径")
    p_error.set_defaults(func=cmd_log_error)

    # 创建log grep子命令解析器
    p_grep = log_sub.add_parser("grep", help="记录匹配日志")
    p_grep.add_argument("file", help="日志文件路径")
    # 如果有两个参数，属性名默认以第一个长参数为准，也就是keyword和limit，没有长参数的时候才是k和n
    p_grep.add_argument("--keyword", "-k", help="匹配关键字")
    p_grep.add_argument("--limit", "-n", type=int, help="限制输出行数")
    p_grep.set_defaults(func=cmd_log_grep)

    # 创建file子命令解析器
    file_p = sub.add_parser("file", help="文件批量处理")
    # 创建file子命令的子命令解析器
    file_sub = file_p.add_subparsers(dest="action", required=True)

    # 创建file rename子命令解析器
    p_rename = file_sub.add_parser("rename", help="批量重命名")
    p_rename.add_argument("directory", help="目录路径")
    p_rename.add_argument("--pattern", "-p", default='*', help="文件匹配模式，例如 *.txt")
    p_rename.add_argument("-r", "--replace", nargs=2, metavar=("OLD", "NEW"), required=True, help="替换旧字符串为新字符串")
    p_rename.add_argument("--dry-run", action="store_true", help="预览重命名结果，不实际执行")
    p_rename.set_defaults(func=cmd_file_rename)

    # 创建file ext子命令解析器
    p_ext = file_sub.add_parser("ext", help="批量修改文件后缀")
    p_ext.add_argument("directory", help="目录路径")
    p_ext.add_argument("--pattern", "-p", default='*', help="文件匹配模式，例如 *.txt")
    p_ext.add_argument("--ext", "-e", required=True, help="新的文件后缀，例如 .log")
    p_ext.add_argument("--dry-run", action="store_true", help="预览修改结果，不实际执行")
    p_ext.set_defaults(func=cmd_file_ext)

    # 创建file clean子命令解析器
    p_clean = file_sub.add_parser("clean", help="批量删除文件")
    p_clean.add_argument("directory", help="目录路径")
    p_clean.add_argument("--pattern", "-p", default='*', help="文件匹配模式，例如 *.tmp")
    p_clean.add_argument("--force", "-f", action="store_true", help="强制删除文件，不提示确认")
    p_clean.add_argument("--dry-run", action="store_true", help="预览删除结果，不实际执行")
    p_clean.set_defaults(func=cmd_file_clean)

    return parser

def main():
    parser = build_parser()
    # 解析命令行参数
    args = parser.parse_args()
    # 如果是file rename命令，将replace参数拆分为old和new两个属性
    if args.command == "file" and args.action == "rename":
        args.old, args.new = args.replace
    try:
        # 调用对应的函数
        args.func(args)
    except KeyboardInterrupt:
        print("\n[中断]用户取消", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[错误]: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()