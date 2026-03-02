#!/usr/bin/env python3
"""
Expense Bot 命令行工具

用法:
    python3 cli.py start          - 启动机器人
    python3 cli.py stop           - 停止机器人
    python3 cli.py restart        - 重启机器人
    python3 cli.py status         - 查看运行状态
    python3 cli.py logs           - 查看日志
    python3 cli.py set <key> <value>  - 设置配置
    python3 cli.py get <key>          - 获取配置
    python3 cli.py list               - 列出所有配置
"""

import argparse
import os
import sys
import yaml
import subprocess
import signal
import time
import socket
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
PID_FILE = PROJECT_ROOT / "data" / "expense-bot.pid"
LOG_FILE = PROJECT_ROOT / "data" / "expense-bot.log"


def load_config() -> dict:
    """加载配置文件."""
    if not CONFIG_FILE.exists():
        print(f"错误: 配置文件不存在: {CONFIG_FILE}")
        sys.exit(1)
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict):
    """保存配置文件."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def get_pid() -> int | None:
    """获取当前运行的 PID."""
    if PID_FILE.exists():
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    return None


def is_running() -> bool:
    """检查进程是否在运行."""
    pid = get_pid()
    if pid is None:
        return False
    
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_bot(daemon: bool = False):
    """启动机器人."""
    if is_running():
        pid = get_pid()
        print(f"机器人已在运行中 (PID: {pid})")
        return
    
    # 确保 data 目录存在
    PROJECT_ROOT.mkdir(exist_ok=True)
    
    if daemon:
        # 后台运行
        print("正在以后台模式启动机器人...")
        
        # 重定向输出到日志文件
        with open(LOG_FILE, "a") as log_file:
            proc = subprocess.Popen(
                [sys.executable, "-m", "bot.main"],
                cwd=PROJECT_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid  # 创建新的进程组
            )
        
        # 保存 PID
        PID_FILE.write_text(str(proc.pid))
        
        # 等待一下让进程启动
        time.sleep(2)
        
        if proc.poll() is None:
            print(f"✓ 机器人已启动 (PID: {proc.pid})")
            print(f"  日志文件: {LOG_FILE}")
        else:
            print("✗ 机器人启动失败")
            sys.exit(1)
    else:
        # 前台运行
        print("正在启动机器人...")
        subprocess.run([sys.executable, "-m", "bot.main"], cwd=PROJECT_ROOT)


def stop_bot():
    """停止机器人."""
    pid = get_pid()
    
    if not is_running():
        print("机器人未在运行")
        # 清理 PID 文件
        if PID_FILE.exists():
            PID_FILE.unlink()
        return
    
    try:
        # 尝试优雅停止
        os.kill(pid, signal.SIGTERM)
        
        # 等待进程结束
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # 强制杀死
            os.kill(pid, signal.SIGKILL)
        
        print("✓ 机器人已停止")
        
    except OSError as e:
        print(f"停止机器人时出错: {e}")
    
    # 清理 PID 文件
    if PID_FILE.exists():
        PID_FILE.unlink()


def restart_bot():
    """重启机器人."""
    print("正在重启机器人...")
    stop_bot()
    time.sleep(1)
    start_bot(daemon=True)


def show_status():
    """显示运行状态."""
    if is_running():
        pid = get_pid()
        print(f"● 机器人运行中 (PID: {pid})")
    else:
        print("○ 机器人未运行")


def show_logs(lines: int = 50):
    """显示日志."""
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            content = f.readlines()
            for line in content[-lines:]:
                print(line, end="")
    else:
        print("日志文件不存在")


def set_config(key: str, value: str):
    """设置配置项."""
    config = load_config()
    
    # 解析嵌套键 (如 bot.token)
    keys = key.split(".")
    current = config
    
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    # 转换值类型
    final_key = keys[-1]
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        # 尝试解析为列表
        try:
            value = eval(value)
        except:
            pass
    
    current[final_key] = value
    
    save_config(config)
    print(f"✓ 已设置 {key} = {value}")


def get_config(key: str = None):
    """获取配置项."""
    config = load_config()
    
    if key is None:
        # 打印所有配置
        print(yaml.dump(config, allow_unicode=True, default_flow_style=False))
        return
    
    # 解析嵌套键
    keys = key.split(".")
    current = config
    
    for k in keys:
        if k not in current:
            print(f"配置项不存在: {key}")
            return
        current = current[k]
    
    print(current)


def list_config():
    """列出所有配置项（格式化）."""
    config = load_config()
    
    print("\n=== Bot 配置 ===")
    print(f"Token: {config.get('bot', {}).get('token', '未设置')[:20]}...")
    print(f"名称: {config.get('bot', {}).get('name', '未设置')}")
    
    print("\n=== 数据库 ===")
    print(f"路径: {config.get('database', {}).get('path', '未设置')}")
    
    print("\n=== 货币 ===")
    currency = config.get('currency', {})
    print(f"符号: {currency.get('symbol', '£')}")
    print(f"名称: {currency.get('name', 'GBP')}")
    
    print("\n=== 设置 ===")
    settings = config.get('settings', {})
    print(f"最大历史记录: {settings.get('max_history', 50)}")
    print(f"时区: {settings.get('timezone', 'UTC')}")
    
    print("\n=== 分类 ===")
    categories = config.get('categories', {})
    expense_cats = categories.get('expense', [])
    income_cats = categories.get('income', [])
    print(f"支出分类: {', '.join(expense_cats[:5])}{'...' if len(expense_cats) > 5 else ''}")
    print(f"收入分类: {', '.join(income_cats[:5])}{'...' if len(income_cats) > 5 else ''}")
    
    print("\n=== 安全 ===")
    allowed = config.get('security', {}).get('allowed_users', [])
    if allowed:
        print(f"允许用户: {allowed}")
    else:
        print("允许用户: 所有人")


def main():
    parser = argparse.ArgumentParser(
        description="Expense Bot 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s start              启动机器人（前台）
    %(prog)s start -d           后台启动机器人
    %(prog)s stop               停止机器人
    %(prog)s restart            重启机器人
    %(prog)s status             查看状态
    %(prog)s logs               查看日志
    %(prog)s logs -n 100        查看最近100行日志
    %(prog)s set bot.token YOUR_TOKEN    设置Token
    %(prog)s set currency.symbol $        设置货币符号
    %(prog)s get bot.token    获取Token
    %(prog)s list             列出所有配置
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # start 命令
    start_parser = subparsers.add_parser("start", help="启动机器人")
    start_parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="以后台模式运行"
    )
    
    # stop 命令
    subparsers.add_parser("stop", help="停止机器人")
    
    # restart 命令
    subparsers.add_parser("restart", help="重启机器人")
    
    # status 命令
    subparsers.add_parser("status", help="查看运行状态")
    
    # logs 命令
    logs_parser = subparsers.add_parser("logs", help="查看日志")
    logs_parser.add_argument(
        "-n", "--lines",
        type=int,
        default=50,
        help="显示的行数 (默认: 50)"
    )
    
    # set 命令
    set_parser = subparsers.add_parser("set", help="设置配置")
    set_parser.add_argument("key", help="配置键 (如 bot.token)")
    set_parser.add_argument("value", help="配置值")
    
    # get 命令
    get_parser = subparsers.add_parser("get", help="获取配置")
    get_parser.add_argument("key", nargs="?", help="配置键 (留空获取所有)")
    
    # list 命令
    subparsers.add_parser("list", help="列出所有配置")
    
    # parse arguments
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # 执行对应命令
    if args.command == "start":
        start_bot(daemon=args.daemon)
    elif args.command == "stop":
        stop_bot()
    elif args.command == "restart":
        restart_bot()
    elif args.command == "status":
        show_status()
    elif args.command == "logs":
        show_logs(lines=args.lines)
    elif args.command == "set":
        set_config(args.key, args.value)
    elif args.command == "get":
        get_config(args.key)
    elif args.command == "list":
        list_config()


if __name__ == "__main__":
    main()
