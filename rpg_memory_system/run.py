#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI游戏记忆系统 - 启动脚本

这个脚本提供了一个统一的入口点来管理整个AI记忆系统，包括:
- 启动API服务器
- 初始化数据库
- 运行测试
- 管理依赖
"""

import asyncio
import subprocess
import sys
import os
import time
from pathlib import Path

# 设置输出编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def print_banner():
    """打印项目横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    AI游戏记忆系统                              ║
║                RPG Memory System                             ║
║                                                              ║
║  基于memobase思想的三层记忆架构                                ║
║  - 短期记忆 (Redis)                                           ║
║  - 核心记忆 (用户画像)                                         ║
║  - 长期记忆 (PostgreSQL + pgvector)                          ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("[ERROR] 错误: 需要Python 3.8或更高版本")
        print(f"当前版本: {sys.version}")
        sys.exit(1)
    else:
        print(f"[OK] Python版本: {sys.version.split()[0]}")

def check_dependencies():
    """检查依赖是否安装"""
    print("\n📦 检查依赖...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'psycopg2', 
        'redis', 'openai', 'langchain', 'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"[OK] {package}")
        except ImportError:
            print(f"[ERROR] {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n[ERROR] 缺少依赖: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """检查环境配置文件"""
    env_file = project_root / '.env'
    if not env_file.exists():
        print("[ERROR] 缺少 .env 配置文件")
        print("请复制 .env.example 并配置相关参数")
        return False
    
    print("[OK] .env 配置文件存在")
    return True

def run_command(command, cwd=None, check=True):
    """运行命令"""
    print(f"🔧 执行: {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd or project_root,
            check=check,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 命令执行失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False
    except UnicodeDecodeError as e:
        print(f"[ERROR] 编码错误: {e}")
        print("提示: 请确保系统编码设置正确")
        return False

def install_dependencies():
    """安装依赖"""
    print("\n📦 安装依赖...")
    return run_command("pip install -r requirements.txt")

def start_database_services():
    """启动数据库服务"""
    print("\n🐳 启动数据库服务...")
    
    # 检查Docker是否可用
    if not run_command("docker --version", check=False):
        print("[ERROR] Docker未安装或不可用")
        print("请手动启动PostgreSQL和Redis服务")
        return False
    
    # 启动docker-compose服务
    if run_command("docker-compose up -d", check=False):
        print("[OK] 数据库服务启动成功")
        print("等待服务就绪...")
        time.sleep(10)  # 等待服务启动
        return True
    else:
        print("[ERROR] 数据库服务启动失败")
        return False

def init_database():
    """初始化数据库"""
    print("\n🗄️ 初始化数据库...")
    return run_command("python scripts/init_database.py init")

def init_npc_stories():
    """初始化NPC故事"""
    print("\n📚 初始化NPC故事...")
    return run_command("python scripts/init_npc_stories.py")

def start_api_server(host="0.0.0.0", port=8000, reload=True):
    """启动API服务器"""
    print(f"\n🚀 启动API服务器 (http://{host}:{port})...")
    
    reload_flag = "--reload" if reload else ""
    command = f"uvicorn src.server.api.api_layer.main:app --host {host} --port {port} {reload_flag}"
    
    try:
        subprocess.run(command, shell=True, cwd=project_root)
    except KeyboardInterrupt:
        print("\n[INFO] API服务器已停止")

def start_api_server_no_reload(host="0.0.0.0", port=8000):
    """启动API服务器（禁用热重载）"""
    print(f"\n🚀 启动API服务器 (http://{host}:{port}) - 禁用热重载...")
    
    command = f"uvicorn src.server.api.api_layer.main:app --host {host} --port {port}"
    
    try:
        subprocess.run(command, shell=True, cwd=project_root)
    except KeyboardInterrupt:
        print("\n[INFO] API服务器已停止")

def run_tests(test_type="all"):
    """运行测试"""
    print(f"\n🧪 运行测试 ({test_type})...")
    
    if test_type == "batch":
        return run_command("python tests/test_batch_simulation.py")
    elif test_type == "interactive":
        return run_command("python tests/test_interactive.py")
    elif test_type == "all":
        print("运行批量测试...")
        if not run_command("python tests/test_batch_simulation.py", check=False):
            print("[WARNING] 批量测试失败")
        
        print("\n启动交互式测试...")
        return run_command("python tests/test_interactive.py")
    else:
        print(f"[ERROR] 未知测试类型: {test_type}")
        return False

def show_help():
    """显示帮助信息"""
    help_text = """
🔧 AI游戏记忆系统 - 管理工具

用法: python run.py <命令> [选项]

命令:
  setup          - 完整设置 (安装依赖 + 启动数据库 + 初始化)
  install        - 安装Python依赖
  db-start       - 启动数据库服务 (Docker)
  db-init        - 初始化数据库表结构
  npc-init       - 初始化NPC故事数据
  server         - 启动API服务器 (开发模式，支持热重载)
  server-stable  - 启动API服务器 (稳定模式，禁用热重载)
  test           - 运行所有测试
  test-batch     - 运行批量测试
  test-interactive - 运行交互式测试
  check          - 检查系统状态
  help           - 显示此帮助信息

示例:
  python run.py setup              # 完整设置系统
  python run.py server             # 启动API服务器
  python run.py test-interactive   # 运行交互式测试
  python run.py check              # 检查系统状态

注意:
  - 首次运行请使用 'setup' 命令
  - 确保已配置 .env 文件
  - 需要Docker来运行数据库服务
    """
    print(help_text)

def check_system_status():
    """检查系统状态"""
    print("\n🔍 检查系统状态...")
    
    # 检查Python版本
    check_python_version()
    
    # 检查环境文件
    check_env_file()
    
    # 检查依赖
    check_dependencies()
    
    # 检查数据库状态
    print("\n🗄️ 检查数据库状态...")
    run_command("python scripts/init_database.py status", check=False)
    
    print("\n[OK] 系统状态检查完成")

def main():
    """主函数"""
    print_banner()
    
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "help":
        show_help()
        
    elif command == "check":
        check_system_status()
        
    elif command == "install":
        check_python_version()
        install_dependencies()
        
    elif command == "db-start":
        start_database_services()
        
    elif command == "db-init":
        init_database()
        
    elif command == "npc-init":
        init_npc_stories()
        
    elif command == "setup":
        print("🚀 开始完整设置...")
        
        # 检查基础环境
        check_python_version()
        if not check_env_file():
            return
            
        # 安装依赖
        if not install_dependencies():
            print("[ERROR] 依赖安装失败")
            return
            
        # 启动数据库服务
        if not start_database_services():
            print("[WARNING] 数据库服务启动失败，请手动启动")
            
        # 初始化数据库
        if not init_database():
            print("[ERROR] 数据库初始化失败")
            return
            
        # 初始化NPC故事
        if not init_npc_stories():
            print("[WARNING] NPC故事初始化失败")
            
        print("\n[OK] 设置完成！")
        print("现在可以运行: python run.py server")
        
    elif command == "server":
        # 检查基础状态
        if not check_dependencies():
            print("请先运行: python run.py install")
            return
            
        # 启动服务器
        start_api_server()
        
    elif command == "server-stable":
        # 检查基础状态
        if not check_dependencies():
            print("请先运行: python run.py install")
            return
            
        # 启动服务器（禁用热重载）
        start_api_server_no_reload()
        
    elif command == "test":
        run_tests("all")
        
    elif command == "test-batch":
        run_tests("batch")
        
    elif command == "test-interactive":
        run_tests("interactive")
        
    else:
        print(f"[ERROR] 未知命令: {command}")
        print("运行 'python run.py help' 查看可用命令")

if __name__ == "__main__":
    main()