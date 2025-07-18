#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能交易大脑 - 主程序入口
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import system_config, monitoring_config
from src.core.engine.trading_engine import TradingEngine
from src.utils.helpers.logger import setup_logger
from src.utils.helpers.signal_handler import setup_signal_handlers


async def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="AI智能交易大脑")
    parser.add_argument("--mode", choices=["simulation", "live"], 
                       default="simulation", help="运行模式")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="日志级别")
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger(
        name="main",
        level=args.log_level,
        debug=args.debug or system_config.DEBUG
    )
    
    try:
        logger.info(f"启动 {system_config.SYSTEM_NAME} v{system_config.VERSION}")
        logger.info(f"运行模式: {args.mode}")
        logger.info(f"调试模式: {args.debug or system_config.DEBUG}")
        
        # 创建交易引擎实例
        engine = TradingEngine(
            simulation_mode=(args.mode == "simulation"),
            debug=args.debug or system_config.DEBUG
        )
        
        # 设置信号处理器
        setup_signal_handlers(engine)
        
        # 初始化引擎
        await engine.initialize()
        
        # 启动引擎
        await engine.start()
        
        logger.info("系统启动成功")
        
        # 保持程序运行
        while engine.is_running():
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到退出信号，正在关闭系统...")
        if 'engine' in locals():
            await engine.stop()
        
    except Exception as e:
        logger.error(f"系统运行异常: {e}", exc_info=True)
        if 'engine' in locals():
            await engine.emergency_stop()
        sys.exit(1)
        
    finally:
        logger.info("系统已关闭")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序异常退出: {e}")
        sys.exit(1)