# -*- coding: utf-8 -*-
"""
交易引擎核心
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
import uuid
from src.ai.models import model_manager, prompt_manager, response_parser
from src.data import collector_manager, processor_manager, storage_manager
from src.utils.helpers.logger import main_logger, trading_logger
from src.utils.helpers.signal_handler import get_signal_handler
from src.utils.helpers.async_utils import async_utils
from config import api_config, db_config, trading_config


class EngineState(Enum):
    """引擎状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    PAUSED = "paused"


class TradingMode(Enum):
    """交易模式"""
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"


@dataclass
class EngineConfig:
    """引擎配置"""
    mode: TradingMode = TradingMode.SIMULATION
    symbols: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    max_concurrent_trades: int = 5
    risk_limit: float = 0.1  # 最大风险限制
    update_interval: int = 10  # 更新间隔（秒）
    auto_start: bool = True
    enable_ai_trading: bool = True
    enable_risk_management: bool = True
    enable_portfolio_optimization: bool = True
    
    # AI配置
    ai_decision_interval: int = 30  # AI决策间隔（秒）
    ai_confidence_threshold: float = 0.7  # AI置信度阈值
    
    # 数据配置
    data_collection_enabled: bool = True
    data_processing_enabled: bool = True
    data_storage_enabled: bool = True


@dataclass
class EngineMetrics:
    """引擎指标"""
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_trade_duration: float = 0.0
    last_trade_time: float = 0.0
    
    # 系统指标
    uptime: float = 0.0
    data_collected_count: int = 0
    ai_decisions_count: int = 0
    errors_count: int = 0
    
    def calculate_win_rate(self):
        """计算胜率"""
        if self.total_trades > 0:
            self.win_rate = self.successful_trades / self.total_trades
            
    def update_drawdown(self, current_balance: float, peak_balance: float):
        """更新回撤"""
        if peak_balance > 0:
            self.current_drawdown = (peak_balance - current_balance) / peak_balance
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)


class TradingEngine:
    """交易引擎"""
    
    def __init__(self, config: EngineConfig):
        self.config = config
        self.state = EngineState.STOPPED
        self.metrics = EngineMetrics()
        self.start_time = 0
        
        # 组件实例
        self.model_manager = model_manager
        self.collector_manager = collector_manager
        self.processor_manager = processor_manager
        self.storage_manager = storage_manager
        
        # 事件回调
        self.event_callbacks: Dict[str, List[Callable]] = {
            "state_changed": [],
            "trade_executed": [],
            "error_occurred": [],
            "data_received": [],
            "ai_decision": []
        }
        
        # 内部状态
        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.market_data_cache: Dict[str, Dict[str, Any]] = {}
        self.last_ai_decision_time = 0
        
        # 任务管理
        self.main_task: Optional[asyncio.Task] = None
        self.background_tasks: List[asyncio.Task] = []
        
        # 错误处理
        self.error_count = 0
        self.last_error_time = 0
        
    def add_event_callback(self, event: str, callback: Callable):
        """添加事件回调"""
        if event in self.event_callbacks:
            self.event_callbacks[event].append(callback)
            main_logger.info(f"添加事件回调: {event} -> {callback.__name__}")
            
    def remove_event_callback(self, event: str, callback: Callable):
        """移除事件回调"""
        if event in self.event_callbacks and callback in self.event_callbacks[event]:
            self.event_callbacks[event].remove(callback)
            main_logger.info(f"移除事件回调: {event} -> {callback.__name__}")
            
    async def _emit_event(self, event: str, data: Any = None):
        """发出事件"""
        if event in self.event_callbacks:
            for callback in self.event_callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    main_logger.error(f"事件回调执行失败 {event}: {e}")
                    
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            main_logger.info("开始初始化交易引擎...")
            
            # 初始化AI模型管理器
            if not await self.model_manager.initialize():
                main_logger.error("AI模型管理器初始化失败")
                return False
                
            # 初始化数据采集器
            if self.config.data_collection_enabled:
                # 创建默认采集器
                collector_ids = self.collector_manager.create_default_collectors()
                main_logger.info(f"创建了 {len(collector_ids)} 个数据采集器")
                
                # 添加数据处理回调
                self.collector_manager.add_data_handler(self._handle_collected_data)
                
            # 初始化数据处理器
            if self.config.data_processing_enabled:
                # 创建默认处理器
                processor_ids = self.processor_manager.create_default_processors()
                main_logger.info(f"创建了 {len(processor_ids)} 个数据处理器")
                
                # 添加结果处理回调
                self.processor_manager.add_result_handler(self._handle_processed_data)
                
            # 初始化存储管理器
            if self.config.data_storage_enabled:
                await self._initialize_storage()
                
            # 设置信号处理器
            signal_handler = get_signal_handler()
            if signal_handler:
                signal_handler.shutdown_callback = self.shutdown
                
            self.state = EngineState.STOPPED
            main_logger.info("交易引擎初始化完成")
            
            return True
            
        except Exception as e:
            main_logger.error(f"交易引擎初始化失败: {e}")
            self.state = EngineState.ERROR
            return False
            
    async def _initialize_storage(self):
        """初始化存储"""
        try:
            # 根据配置创建存储实例
            if Config.DATABASE.POSTGRESQL_ENABLED:
                from src.data.storage.data_storage import PostgreSQLStorage, StorageConfig, StorageType
                
                pg_config = StorageConfig(
                    storage_type=StorageType.POSTGRESQL,
                    connection_params={
                        "host": Config.DATABASE.POSTGRESQL_HOST,
                        "port": Config.DATABASE.POSTGRESQL_PORT,
                        "database": Config.DATABASE.POSTGRESQL_DB,
                        "user": Config.DATABASE.POSTGRESQL_USER,
                        "password": Config.DATABASE.POSTGRESQL_PASSWORD
                    }
                )
                
                pg_storage = PostgreSQLStorage(pg_config)
                self.storage_manager.add_storage("postgresql", pg_storage)
                
            # Redis存储
            if Config.DATABASE.REDIS_ENABLED:
                from src.data.storage.data_storage import RedisStorage, StorageConfig, StorageType
                
                redis_config = StorageConfig(
                    storage_type=StorageType.REDIS,
                    connection_params={
                        "host": Config.DATABASE.REDIS_HOST,
                        "port": Config.DATABASE.REDIS_PORT,
                        "password": Config.DATABASE.REDIS_PASSWORD,
                        "db": Config.DATABASE.REDIS_DB
                    }
                )
                
                redis_storage = RedisStorage(redis_config)
                self.storage_manager.add_storage("redis", redis_storage)
                
            # 内存存储（备用）
            from src.data.storage.data_storage import MemoryStorage, StorageConfig, StorageType
            
            memory_config = StorageConfig(
                storage_type=StorageType.MEMORY,
                connection_params={"max_size": 50000}
            )
            
            memory_storage = MemoryStorage(memory_config)
            self.storage_manager.add_storage("memory", memory_storage)
            
            # 连接所有存储
            await self.storage_manager.connect_all()
            
        except Exception as e:
            main_logger.error(f"存储初始化失败: {e}")
            
    async def start(self) -> bool:
        """启动引擎"""
        if self.state == EngineState.RUNNING:
            main_logger.warning("交易引擎已在运行")
            return True
            
        try:
            self.state = EngineState.STARTING
            self.start_time = time.time()
            
            await self._emit_event("state_changed", self.state)
            
            # 启动数据采集
            if self.config.data_collection_enabled:
                await self.collector_manager.start_all_collectors()
                
            # 启动数据处理
            if self.config.data_processing_enabled:
                await self.processor_manager.start_processing()
                
            # 启动主循环
            self.main_task = asyncio.create_task(self._main_loop())
            
            # 启动后台任务
            self.background_tasks = [
                asyncio.create_task(self._metrics_update_loop()),
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._cleanup_loop())
            ]
            
            self.state = EngineState.RUNNING
            await self._emit_event("state_changed", self.state)
            
            main_logger.info("交易引擎启动成功")
            return True
            
        except Exception as e:
            self.state = EngineState.ERROR
            await self._emit_event("state_changed", self.state)
            main_logger.error(f"交易引擎启动失败: {e}")
            return False
            
    async def stop(self) -> bool:
        """停止引擎"""
        if self.state == EngineState.STOPPED:
            main_logger.warning("交易引擎已停止")
            return True
            
        try:
            self.state = EngineState.STOPPING
            await self._emit_event("state_changed", self.state)
            
            # 停止主任务
            if self.main_task and not self.main_task.done():
                self.main_task.cancel()
                try:
                    await self.main_task
                except asyncio.CancelledError:
                    pass
                    
            # 停止后台任务
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                        
            # 停止数据采集
            if self.config.data_collection_enabled:
                await self.collector_manager.stop_all_collectors()
                
            # 停止数据处理
            if self.config.data_processing_enabled:
                await self.processor_manager.stop_processing()
                
            # 关闭存储连接
            if self.config.data_storage_enabled:
                await self.storage_manager.disconnect_all()
                
            self.state = EngineState.STOPPED
            await self._emit_event("state_changed", self.state)
            
            main_logger.info("交易引擎停止成功")
            return True
            
        except Exception as e:
            self.state = EngineState.ERROR
            await self._emit_event("state_changed", self.state)
            main_logger.error(f"交易引擎停止失败: {e}")
            return False
            
    async def pause(self):
        """暂停引擎"""
        if self.state == EngineState.RUNNING:
            self.state = EngineState.PAUSED
            await self._emit_event("state_changed", self.state)
            main_logger.info("交易引擎已暂停")
            
    async def resume(self):
        """恢复引擎"""
        if self.state == EngineState.PAUSED:
            self.state = EngineState.RUNNING
            await self._emit_event("state_changed", self.state)
            main_logger.info("交易引擎已恢复")
            
    def is_running(self) -> bool:
        """检查引擎是否正在运行"""
        return self.state == EngineState.RUNNING
        
    async def emergency_stop(self):
        """紧急停止引擎"""
        main_logger.warning("紧急停止交易引擎...")
        
        try:
            # 立即设置为停止状态
            self.state = EngineState.STOPPING
            await self._emit_event("state_changed", self.state)
            
            # 强制取消所有任务
            if self.main_task and not self.main_task.done():
                self.main_task.cancel()
                
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
                    
            # 强制停止组件
            await self.collector_manager.stop_all_collectors()
            await self.processor_manager.stop_processing()
            await self.storage_manager.disconnect_all()
            
            self.state = EngineState.STOPPED
            await self._emit_event("state_changed", self.state)
            
            main_logger.info("紧急停止完成")
            
        except Exception as e:
            main_logger.error(f"紧急停止失败: {e}")
            self.state = EngineState.ERROR
    
    async def shutdown(self):
        """关闭引擎"""
        main_logger.info("开始关闭交易引擎...")
        
        # 停止引擎
        await self.stop()
        
        # 关闭AI模型管理器
        await self.model_manager.close()
        
        # 关闭异步工具
        async_utils.close()
        
        main_logger.info("交易引擎关闭完成")
        
    async def _main_loop(self):
        """主循环"""
        while self.state == EngineState.RUNNING:
            try:
                # 检查是否暂停
                if self.state == EngineState.PAUSED:
                    await asyncio.sleep(1)
                    continue
                    
                # 执行AI决策
                if self.config.enable_ai_trading:
                    await self._execute_ai_decision()
                    
                # 更新市场数据
                await self._update_market_data()
                
                # 检查活跃交易
                await self._check_active_trades()
                
                # 等待下次循环
                await asyncio.sleep(self.config.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error_count += 1
                self.last_error_time = time.time()
                await self._emit_event("error_occurred", {"error": str(e), "context": "main_loop"})
                main_logger.error(f"主循环异常: {e}")
                
                # 如果错误过多，暂停引擎
                if self.error_count > 10:
                    await self.pause()
                    
    async def _execute_ai_decision(self):
        """执行AI决策"""
        current_time = time.time()
        
        # 检查决策间隔
        if current_time - self.last_ai_decision_time < self.config.ai_decision_interval:
            return
            
        try:
            # 为每个交易对执行决策
            for symbol in self.config.symbols:
                await self._make_ai_decision(symbol)
                
            self.last_ai_decision_time = current_time
            self.metrics.ai_decisions_count += 1
            
        except Exception as e:
            main_logger.error(f"AI决策执行失败: {e}")
            
    async def _make_ai_decision(self, symbol: str):
        """为特定交易对做出AI决策"""
        try:
            # 获取市场数据
            market_data = self.market_data_cache.get(symbol, {})
            
            if not market_data:
                return
                
            # 构建AI请求
            from src.ai.models import ModelRequest, ModelType
            
            # 使用交易决策模板
            template_vars = {
                "symbol": symbol,
                "current_price": market_data.get("price", 0),
                "account_balance": 10000,  # 模拟账户余额
                "current_position": self.active_trades.get(symbol, {}),
                "risk_level": "medium",
                "market_analysis": "待分析",
                "technical_indicators": market_data.get("indicators", {}),
                "risk_metrics": {"var": 0.05, "max_drawdown": 0.1}
            }
            
            formatted_prompt = prompt_manager.format_prompt("trading_decision", template_vars)
            
            if not formatted_prompt:
                return
                
            # 创建AI请求
            ai_request = ModelRequest(
                prompt=formatted_prompt["user_prompt"],
                model_type=ModelType.QWEN_LONG,
                system_message=formatted_prompt["system_message"],
                temperature=0.7,
                max_tokens=2000
            )
            
            # 获取AI响应
            ai_response = await self.model_manager.generate(ai_request)
            
            if ai_response and ai_response.confidence >= self.config.ai_confidence_threshold:
                # 解析AI响应
                from src.ai.models import ResponseType
                
                parsed_response = response_parser.parse_response(
                    ai_response.content, 
                    ResponseType.TRADING_DECISION
                )
                
                # 处理AI决策
                await self._process_ai_decision(symbol, parsed_response)
                
                await self._emit_event("ai_decision", {
                    "symbol": symbol,
                    "decision": parsed_response,
                    "confidence": ai_response.confidence
                })
                
        except Exception as e:
            main_logger.error(f"AI决策失败 ({symbol}): {e}")
            
    async def _process_ai_decision(self, symbol: str, decision):
        """处理AI决策"""
        try:
            if not decision.structured_data:
                return
                
            decision_data = decision.structured_data
            action = decision_data.get("decision", "hold")
            
            if action == "buy":
                await self._execute_buy_order(symbol, decision_data)
            elif action == "sell":
                await self._execute_sell_order(symbol, decision_data)
            elif action == "hold":
                main_logger.info(f"AI决策: 持有 {symbol}")
                
        except Exception as e:
            main_logger.error(f"处理AI决策失败 ({symbol}): {e}")
            
    async def _execute_buy_order(self, symbol: str, decision_data: Dict[str, Any]):
        """执行买单"""
        try:
            # 模拟交易执行
            trade_id = str(uuid.uuid4())
            
            trade_info = {
                "id": trade_id,
                "symbol": symbol,
                "side": "buy",
                "amount": decision_data.get("position_size", 0.01),
                "price": decision_data.get("entry_price", 0),
                "timestamp": time.time(),
                "status": "executed",
                "stop_loss": decision_data.get("stop_loss"),
                "take_profit": decision_data.get("take_profit")
            }
            
            self.active_trades[symbol] = trade_info
            
            # 更新指标
            self.metrics.total_trades += 1
            self.metrics.last_trade_time = time.time()
            
            await self._emit_event("trade_executed", trade_info)
            
            trading_logger.info(f"买单执行: {symbol} @ {trade_info['price']}")
            
        except Exception as e:
            main_logger.error(f"买单执行失败 ({symbol}): {e}")
            
    async def _execute_sell_order(self, symbol: str, decision_data: Dict[str, Any]):
        """执行卖单"""
        try:
            # 检查是否有持仓
            if symbol not in self.active_trades:
                return
                
            # 模拟交易执行
            trade_info = self.active_trades[symbol]
            trade_info["status"] = "closed"
            trade_info["close_price"] = decision_data.get("entry_price", 0)
            trade_info["close_timestamp"] = time.time()
            
            # 计算PnL
            if trade_info["side"] == "buy":
                pnl = (trade_info["close_price"] - trade_info["price"]) * trade_info["amount"]
            else:
                pnl = (trade_info["price"] - trade_info["close_price"]) * trade_info["amount"]
                
            trade_info["pnl"] = pnl
            
            # 更新指标
            self.metrics.total_pnl += pnl
            
            if pnl > 0:
                self.metrics.successful_trades += 1
            else:
                self.metrics.failed_trades += 1
                
            self.metrics.calculate_win_rate()
            
            # 移除活跃交易
            del self.active_trades[symbol]
            
            await self._emit_event("trade_executed", trade_info)
            
            trading_logger.info(f"卖单执行: {symbol} @ {trade_info['close_price']}, PnL: {pnl}")
            
        except Exception as e:
            main_logger.error(f"卖单执行失败 ({symbol}): {e}")
            
    async def _update_market_data(self):
        """更新市场数据"""
        # 这里可以从数据缓存中获取最新市场数据
        pass
        
    async def _check_active_trades(self):
        """检查活跃交易"""
        # 检查止损止盈等
        pass
        
    async def _handle_collected_data(self, data):
        """处理采集到的数据"""
        try:
            # 更新市场数据缓存
            if data.data_type.value in ["ticker", "kline"]:
                self.market_data_cache[data.symbol] = data.data
                
            # 提交数据处理
            await self.processor_manager.submit_data(data)
            
            # 存储数据
            if self.config.data_storage_enabled:
                await self.storage_manager.store_data(data)
                
            self.metrics.data_collected_count += 1
            
            await self._emit_event("data_received", data)
            
        except Exception as e:
            main_logger.error(f"处理采集数据失败: {e}")
            
    async def _handle_processed_data(self, data):
        """处理处理后的数据"""
        try:
            # 存储处理后的数据
            if self.config.data_storage_enabled:
                await self.storage_manager.store_data(data)
                
        except Exception as e:
            main_logger.error(f"处理处理后数据失败: {e}")
            
    async def _metrics_update_loop(self):
        """指标更新循环"""
        while self.state in [EngineState.RUNNING, EngineState.PAUSED]:
            try:
                # 更新运行时间
                if self.start_time > 0:
                    self.metrics.uptime = time.time() - self.start_time
                    
                await asyncio.sleep(60)  # 每分钟更新一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                main_logger.error(f"指标更新循环异常: {e}")
                
    async def _health_check_loop(self):
        """健康检查循环"""
        while self.state in [EngineState.RUNNING, EngineState.PAUSED]:
            try:
                # 检查各组件健康状态
                await self._perform_health_check()
                
                await asyncio.sleep(300)  # 每5分钟检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                main_logger.error(f"健康检查循环异常: {e}")
                
    async def _perform_health_check(self):
        """执行健康检查"""
        try:
            # 检查AI模型状态
            model_status = self.model_manager.get_model_status()
            
            # 检查数据采集器状态
            collector_status = self.collector_manager.get_all_status()
            
            # 检查数据处理器状态
            processor_status = self.processor_manager.get_all_status()
            
            # 检查存储状态
            storage_status = self.storage_manager.get_storage_status()
            
            # 记录健康状态
            main_logger.debug(f"健康检查完成: AI模型正常, 采集器运行 {len(self.collector_manager.collectors)}, 处理器运行 {len(self.processor_manager.processors)}")
            
        except Exception as e:
            main_logger.error(f"健康检查失败: {e}")
            
    async def _cleanup_loop(self):
        """清理循环"""
        while self.state in [EngineState.RUNNING, EngineState.PAUSED]:
            try:
                # 清理旧数据
                if self.config.data_storage_enabled:
                    await self.storage_manager.cleanup_all()
                    
                await asyncio.sleep(3600)  # 每小时清理一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                main_logger.error(f"清理循环异常: {e}")
                
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "state": self.state.value,
            "mode": self.config.mode.value,
            "uptime": self.metrics.uptime,
            "symbols": self.config.symbols,
            "active_trades": len(self.active_trades),
            "error_count": self.error_count,
            "last_error_time": self.last_error_time,
            "metrics": {
                "total_trades": self.metrics.total_trades,
                "successful_trades": self.metrics.successful_trades,
                "failed_trades": self.metrics.failed_trades,
                "win_rate": self.metrics.win_rate,
                "total_pnl": self.metrics.total_pnl,
                "max_drawdown": self.metrics.max_drawdown,
                "data_collected_count": self.metrics.data_collected_count,
                "ai_decisions_count": self.metrics.ai_decisions_count
            }
        }
        
    def get_active_trades(self) -> Dict[str, Any]:
        """获取活跃交易"""
        return self.active_trades.copy()
        
    def get_market_data(self) -> Dict[str, Any]:
        """获取市场数据"""
        return self.market_data_cache.copy()


# 创建全局交易引擎实例
def create_trading_engine(config: EngineConfig = None) -> TradingEngine:
    """创建交易引擎实例"""
    if config is None:
        config = EngineConfig()
        
    return TradingEngine(config)