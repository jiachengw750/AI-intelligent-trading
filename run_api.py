#!/usr/bin/env python3
"""
AI智能交易大脑API启动脚本
"""
import os
import sys
import argparse
import uvicorn
from pathlib import Path


def setup_environment():
    """设置环境变量和路径"""
    # 添加项目根目录到Python路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # 设置环境变量
    os.environ.setdefault("PYTHONPATH", str(project_root))
    
    # 日志目录
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    return project_root


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI智能交易大脑API服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听主机")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开启热重载")
    parser.add_argument("--log-level", default="info", help="日志级别")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")
    parser.add_argument("--env", default="development", help="运行环境")
    
    args = parser.parse_args()
    
    # 设置环境
    project_root = setup_environment()
    
    # 根据环境配置不同的参数
    if args.env == "production":
        config = {
            "app": "src.api.main:app",
            "host": args.host,
            "port": args.port,
            "workers": args.workers,
            "log_level": args.log_level,
            "access_log": True,
            "use_colors": False,
            "server_header": False,
            "date_header": False,
            "proxy_headers": True,
            "forwarded_allow_ips": "*",
            "timeout_keep_alive": 30
        }
    else:
        config = {
            "app": "src.api.main:app",
            "host": args.host,
            "port": args.port,
            "reload": args.reload,
            "log_level": args.log_level,
            "access_log": True,
            "use_colors": True,
            "server_header": False,
            "date_header": False,
            "reload_dirs": [str(project_root / "src")]
        }
    
    print("=" * 60)
    print("AI智能交易大脑API")
    print("=" * 60)
    print(f"环境: {args.env}")
    print(f"主机: {args.host}")
    print(f"端口: {args.port}")
    print(f"重载: {args.reload}")
    print(f"日志级别: {args.log_level}")
    print(f"工作进程: {args.workers if args.env == 'production' else 1}")
    print("=" * 60)
    print("API文档地址:")
    print(f"  Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"  ReDoc: http://{args.host}:{args.port}/redoc")
    print(f"  OpenAPI: http://{args.host}:{args.port}/openapi.json")
    print("=" * 60)
    print("启动中...")
    print()
    
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()