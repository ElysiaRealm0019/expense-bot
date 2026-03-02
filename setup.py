#!/usr/bin/env python3
"""
expense-bot 自动配置脚本

自动完成:
1. 创建 ~/.config/expense-bot/ 目录
2. 复制配置文件到新位置
3. 配置权限
"""

import os
import shutil
import stat
from pathlib import Path


def get_config_dir() -> Path:
    """获取配置目录路径"""
    return Path.home() / ".config" / "expense-bot"


def get_data_dir() -> Path:
    """获取数据目录路径"""
    return Path.home() / ".local" / "share" / "expense-bot"


def get_script_dir() -> Path:
    """获取脚本所在目录"""
    return Path(__file__).parent.resolve()


def setup():
    """执行自动配置"""
    script_dir = get_script_dir()
    config_dir = get_config_dir()
    data_dir = get_data_dir()
    
    print("📁 开始配置 expense-bot...")
    print()
    
    # 1. 创建配置目录
    print(f"➤ 创建配置目录: {config_dir}")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. 复制配置文件
    print("➤ 复制配置文件...")
    
    # 优先复制 .env.example
    env_example = script_dir / ".env.example"
    env_target = config_dir / ".env"
    
    if env_example.exists():
        shutil.copy2(env_example, env_target)
        print(f"  ✓ .env.example → {env_target}")
    else:
        print("  ✗ 未找到 .env.example")
    
    # 复制 config.yaml (如果存在)
    config_yaml = script.yaml"
    config_yaml_target = config_dir / "config_dir / "config.yaml"
    
    if config_yaml.exists():
        shutil.copy2(config_yaml, config_yaml_target)
        print(f"  ✓ config.yaml → {config_yaml_target}")
    
    # 3. 配置权限
    print("➤ 配置权限...")
    
    # 设置目录权限为 700 (仅所有者)
    os.chmod(config_dir, stat.S_IRWXU)
    print(f"  ✓ 目录权限: 700")
    
    # 设置 .env 权限为 600 (仅所有者可读写)
    if env_target.exists():
        os.chmod(env_target, stat.S_IRUSR | stat.S_IWUSR)
        print(f"  ✓ .env 权限: 600")
    
    # 4. 创建数据目录
    print("➤ 创建数据目录...")
    data_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(data_dir, stat.S_IRWXU)
    print(f"  ✓ {data_dir}")
    
    print()
    print("✅ 配置完成!")
    print()
    print("后续步骤:")
    print(f"  1. 编辑 {env_target}")
    print("  2. 填入您的 Telegram Bot Token")
    print(f"  3. 运行: cd {script_dir} && python -m expense_bot")


if __name__ == "__main__":
    setup()
