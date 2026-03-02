"""
CLI 入口模块 - 命令行参数解析

Usage:
    python3 -m expense_bot.cli --help
    python3 -m expense_bot.cli start
    python3 -m expense_bot.cli start --daemon
    python3 -m expense_bot.cli config set token "xxx"
    python3 -m expense_bot.cli config get currency.symbol
    python3 -m expense_bot.cli status
    python3 -m expense_bot.cli restart
    python3 -m expense_bot.cli stop
"""

import argparse
import os
import sys
import yaml
import logging
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config() -> dict:
    """加载配置文件"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict):
    """保存配置文件"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)


def cmd_start(args):
    """启动机器人"""
    from bot.main import main as bot_main
    
    if args.daemon:
        # 后台运行模式
        import subprocess
        import socket
        
        # 检查端口是否被占用
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', args.port))
        sock.close()
        
        if result == 0:
            print(f"❌ 端口 {args.port} 已被占用，机器人可能已在运行")
            sys.exit(1)
        
        # 创建日志目录
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "bot.log"
        
        # 使用 nohup 后台运行
        cmd = [
            "nohup",
            sys.executable, "-m", "bot.main",
            f">> {log_file}", "2>&1",
            "&"
        ]
        
        print(f"🚀 启动机器人 (后台模式)...")
        print(f"📝 日志文件: {log_file}")
        
        # 写入PID文件
        pid_file = PROJECT_ROOT / "bot.pid"
        
        # 直接启动进程
        with open(log_file, "a") as log:
            proc = subprocess.Popen(
                [sys.executable, "-m", "bot.main"],
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT)
            )
        
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        
        print(f"✅ 机器人已启动 (PID: {proc.pid})")
        print(f"📄 PID文件: {pid_file}")
        
    else:
        # 前台运行模式
        print("🚀 启动机器人 (前台模式)...")
        bot_main()


def cmd_stop(args):
    """停止机器人"""
    pid_file = PROJECT_ROOT / "bot.pid"
    
    if not pid_file.exists():
        # 尝试通过端口查找进程
        import subprocess
        result = subprocess.run(
            ["lsof", "-ti", f":{args.port}"],
            capture_output=True,
            text=True
        )
        if result.stdout:
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                try:
                    import signal
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"✅ 已终止进程 (PID: {pid})")
                except ProcessLookupError:
                    pass
        else:
            print("❌ 未找到运行中的机器人进程")
        return
    
    with open(pid_file, "r") as f:
        pid = int(f.read().strip())
    
    try:
        import signal
        os.kill(pid, signal.SIGTERM)
        print(f"✅ 已发送终止信号 (PID: {pid})")
        
        # 等待进程结束
        import time
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("✅ 机器人已停止")
                break
        else:
            print("⚠️ 进程未响应，强制终止...")
            os.kill(pid, signal.SIGKILL)
        
        pid_file.unlink()
        
    except ProcessLookupError:
        print("❌ 进程不存在，已清理PID文件")
        pid_file.unlink()
    except PermissionError:
        print("❌ 无权限终止进程，请使用sudo")


def cmd_status(args):
    """查看机器人状态"""
    pid_file = PROJECT_ROOT / "bot.pid"
    
    if not pid_file.exists():
        print("📊 机器人状态: 未运行")
        print("   使用 'start' 命令启动机器人")
        return
    
    with open(pid_file, "r") as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, 0)
        print(f"📊 机器人状态: 运行中")
        print(f"   PID: {pid}")
    except ProcessLookupError:
        print("📊 机器人状态: 已停止 (PID文件过期)")
        pid_file.unlink()


def cmd_restart(args):
    """重启机器人"""
    print("🔄 重启机器人...")
    cmd_stop(args)
    import time
    time.sleep(1)
    cmd_start(args)


def cmd_config(args):
    """配置管理"""
    config = load_config()
    
    if args.config_action == "get":
        # 获取配置
        keys = args.key.split(".")
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                print(f"❌ 配置项不存在: {args.key}")
                sys.exit(1)
        
        print(f"{args.key} = {value}")
        return
    
    elif args.config_action == "set":
        # 设置配置
        keys = args.key.split(".")
        
        # 导航到嵌套结构
        target = config
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # 设置值
        target[keys[-1]] = args.value
        
        save_config(config)
        print(f"✅ 已设置 {args.key} = {args.value}")
        
    elif args.config_action == "list":
        # 列出所有配置
        print("📋 当前配置:")
        print(yaml.dump(config, allow_unicode=True, default_flow_style=False))


def cmd_systemd(args):
    """Systemd 服务管理"""
    import subprocess
    
    service_name = "expense-bot"
    service_file = f"/etc/systemd/system/{service_name}.service"
    
    if args.systemd_action == "install":
        # 检查是否有root权限
        if os.geteuid() != 0:
            print("⚠️ 安装systemd服务需要root权限，请运行: sudo ...")
            return
        
        # 生成服务文件
        service_content = f"""[Unit]
Description=Telegram Expense Bot
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'clawbot')}
WorkingDirectory={PROJECT_ROOT}
ExecStart={sys.executable} -m bot.main
Restart=always
RestartSec=10
StandardOutput=append:{PROJECT_ROOT}/logs/bot.log
StandardError=append:{PROJECT_ROOT}/logs/bot.log

[Install]
WantedBy=multi-user.target
"""
        
        with open(service_file, "w") as f:
            f.write(service_content)
        
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", service_name])
        
        print(f"✅ systemd服务已安装: {service_name}")
        print(f"   服务文件: {service_file}")
        print(f"   使用以下命令管理:")
        print(f"   - 启动: sudo systemctl start {service_name}")
        print(f"   - 停止: sudo systemctl stop {service_name}")
        print(f"   - 查看日志: sudo journalctl -u {service_name} -f")
        
    elif args.systemd_action == "uninstall":
        if os.geteuid() != 0:
            print("⚠️ 卸载systemd服务需要root权限")
            return
        
        subprocess.run(["systemctl", "stop", service_name], capture_output=True)
        subprocess.run(["systemctl", "disable", service_name], capture_output=True)
        
        if os.path.exists(service_file):
            os.remove(service_file)
        
        subprocess.run(["systemctl", "daemon-reload"])
        print(f"✅ systemd服务已卸载")


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="Telegram Expense Bot CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s start                    # 前台启动
  %(prog)s start --daemon           # 后台启动
  %(prog)s stop                     # 停止
  %(prog)s status                   # 查看状态
  %(prog)s restart                  # 重启
  %(prog)s config set token "xxx"   # 设置token
  %(prog)s config get currency.symbol  # 获取货币符号
  %(prog)s config list              # 列出所有配置
  %(prog)s systemd install          # 安装systemd服务
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # start 命令
    start_parser = subparsers.add_parser("start", help="启动机器人")
    start_parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="以后台模式运行"
    )
    start_parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="检查占用的端口 (默认: 8080)"
    )
    start_parser.set_defaults(func=cmd_start)
    
    # stop 命令
    stop_parser = subparsers.add_parser("stop", help="停止机器人")
    stop_parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="机器人运行端口"
    )
    stop_parser.set_defaults(func=cmd_stop)
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="查看状态")
    status_parser.set_defaults(func=cmd_status)
    
    # restart 命令
    restart_parser = subparsers.add_parser("restart", help="重启机器人")
    restart_parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="机器人运行端口"
    )
    restart_parser.set_defaults(func=cmd_restart)
    
    # config 命令
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_subparsers = config_parser.add_subparsers(
        dest="config_action",
        help="配置操作"
    )
    
    # config get
    get_parser = config_subparsers.add_parser("get", help="获取配置")
    get_parser.add_argument("key", help="配置键 (如: currency.symbol)")
    get_parser.set_defaults(func=cmd_config)
    
    # config set
    set_parser = config_subparsers.add_parser("set", help="设置配置")
    set_parser.add_argument("key", help="配置键 (如: currency.symbol)")
    set_parser.add_argument("value", help="配置值")
    set_parser.set_defaults(func=cmd_config)
    
    # config list
    list_parser = config_subparsers.add_parser("list", help="列出配置")
    list_parser.set_defaults(func=cmd_config)
    
    # systemd 命令
    systemd_parser = subparsers.add_parser("systemd", help="Systemd服务管理")
    systemd_subparsers = systemd_parser.add_subparsers(
        dest="systemd_action",
        help="systemd操作"
    )
    
    systemd_subparsers.add_parser("install", help="安装systemd服务").set_defaults(
        func=cmd_systemd
    )
    systemd_subparsers.add_parser("uninstall", help="卸载systemd服务").set_defaults(
        func=cmd_systemd
    )
    
    return parser


def main():
    """CLI 主入口"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 确保日志目录存在
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        logging.exception("CLI error")
        sys.exit(1)


if __name__ == "__main__":
    main()
