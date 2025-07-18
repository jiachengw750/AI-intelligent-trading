# -*- coding: utf-8 -*-
"""
异步任务调度器
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import heapq
from concurrent.futures import ThreadPoolExecutor
from src.utils.helpers.logger import get_logger
from src.core.exceptions.trading_exceptions import TaskException

logger = get_logger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0  # 关键任务
    HIGH = 1      # 高优先级
    NORMAL = 2    # 普通优先级
    LOW = 3       # 低优先级
    IDLE = 4      # 空闲任务


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class Task:
    """任务对象"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[Exception] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """比较优先级（用于优先队列）"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at
        
    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """检查任务是否准备好执行"""
        return self.dependencies.issubset(completed_tasks)
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "priority": self.priority.name,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
            "dependencies": list(self.dependencies),
            "metadata": self.metadata
        }


class TaskScheduler:
    """异步任务调度器"""
    
    def __init__(self, max_workers: int = 10, max_queue_size: int = 10000):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        
        # 任务队列（优先队列）
        self.task_queue: List[Task] = []
        self.queue_lock = asyncio.Lock()
        
        # 任务映射
        self.tasks: Dict[str, Task] = {}
        self.completed_tasks: Set[str] = set()
        
        # 工作线程
        self.workers: List[asyncio.Task] = []
        self.worker_semaphore = asyncio.Semaphore(max_workers)
        
        # 线程池（用于CPU密集型任务）
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers // 2)
        
        # 调度器状态
        self.is_running = False
        self.stats = defaultdict(int)
        
        # 任务组管理
        self.task_groups: Dict[str, List[str]] = defaultdict(list)
        
        # 定时任务
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}
        
    async def start(self):
        """启动调度器"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
            
        # 启动定时任务检查器
        asyncio.create_task(self._scheduled_task_checker())
        
        logger.info(f"任务调度器启动，工作线程数: {self.max_workers}")
        
    async def stop(self):
        """停止调度器"""
        self.is_running = False
        
        # 取消所有工作线程
        for worker in self.workers:
            worker.cancel()
            
        # 等待工作线程结束
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        logger.info("任务调度器已停止")
        
    async def submit_task(
        self,
        func: Callable,
        *args,
        name: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        dependencies: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """提交任务"""
        async with self.queue_lock:
            if len(self.task_queue) >= self.max_queue_size:
                raise TaskException("任务队列已满")
                
            task = Task(
                name=name or func.__name__,
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
                dependencies=dependencies or set(),
                metadata=metadata or {}
            )
            
            # 添加到任务映射
            self.tasks[task.id] = task
            
            # 添加到优先队列
            heapq.heappush(self.task_queue, task)
            
            self.stats["submitted"] += 1
            
            logger.debug(f"提交任务: {task.name} (ID: {task.id})")
            
            return task.id
            
    async def submit_batch(
        self,
        tasks: List[Dict[str, Any]],
        group_name: Optional[str] = None
    ) -> List[str]:
        """批量提交任务"""
        task_ids = []
        
        for task_config in tasks:
            func = task_config.pop("func")
            task_id = await self.submit_task(func, **task_config)
            task_ids.append(task_id)
            
            if group_name:
                self.task_groups[group_name].append(task_id)
                
        logger.info(f"批量提交 {len(task_ids)} 个任务")
        
        return task_ids
        
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
        
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self.stats["cancelled"] += 1
            return True
        return False
        
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """等待任务完成"""
        start_time = time.time()
        
        while True:
            task = self.tasks.get(task_id)
            if not task:
                raise TaskException(f"任务不存在: {task_id}")
                
            if task.status == TaskStatus.COMPLETED:
                return task.result
            elif task.status == TaskStatus.FAILED:
                raise task.error or TaskException(f"任务失败: {task_id}")
            elif task.status == TaskStatus.CANCELLED:
                raise TaskException(f"任务已取消: {task_id}")
                
            if timeout and (time.time() - start_time) > timeout:
                raise TaskException(f"等待任务超时: {task_id}")
                
            await asyncio.sleep(0.1)
            
    async def wait_for_group(
        self,
        group_name: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """等待任务组完成"""
        task_ids = self.task_groups.get(group_name, [])
        if not task_ids:
            return {}
            
        results = {}
        errors = {}
        
        # 并行等待所有任务
        tasks = []
        for task_id in task_ids:
            tasks.append(self.wait_for_task(task_id, timeout))
            
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for task_id, result in zip(task_ids, completed):
            if isinstance(result, Exception):
                errors[task_id] = str(result)
            else:
                results[task_id] = result
                
        return {
            "results": results,
            "errors": errors,
            "total": len(task_ids),
            "succeeded": len(results),
            "failed": len(errors)
        }
        
    async def schedule_task(
        self,
        func: Callable,
        interval: Union[int, timedelta],
        name: str,
        *args,
        start_time: Optional[datetime] = None,
        **kwargs
    ) -> str:
        """添加定时任务"""
        task_id = str(uuid.uuid4())
        
        if isinstance(interval, int):
            interval = timedelta(seconds=interval)
            
        self.scheduled_tasks[task_id] = {
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "interval": interval,
            "name": name,
            "last_run": None,
            "next_run": start_time or datetime.now()
        }
        
        logger.info(f"添加定时任务: {name} (间隔: {interval})")
        
        return task_id
        
    async def cancel_scheduled_task(self, task_id: str) -> bool:
        """取消定时任务"""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            return True
        return False
        
    async def _worker(self, worker_name: str):
        """工作线程"""
        logger.debug(f"{worker_name} 启动")
        
        while self.is_running:
            try:
                # 获取下一个任务
                task = await self._get_next_task()
                if not task:
                    await asyncio.sleep(0.1)
                    continue
                    
                # 获取工作许可
                async with self.worker_semaphore:
                    await self._execute_task(task)
                    
            except Exception as e:
                logger.error(f"{worker_name} 错误: {e}")
                
        logger.debug(f"{worker_name} 停止")
        
    async def _get_next_task(self) -> Optional[Task]:
        """获取下一个待执行的任务"""
        async with self.queue_lock:
            # 查找准备好的任务
            ready_tasks = []
            temp_queue = []
            
            while self.task_queue:
                task = heapq.heappop(self.task_queue)
                
                if task.status == TaskStatus.CANCELLED:
                    continue
                    
                if task.is_ready(self.completed_tasks):
                    ready_tasks.append(task)
                    break
                else:
                    temp_queue.append(task)
                    
            # 将未准备好的任务放回队列
            for task in temp_queue:
                heapq.heappush(self.task_queue, task)
                
            if ready_tasks:
                task = ready_tasks[0]
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                return task
                
            return None
            
    async def _execute_task(self, task: Task):
        """执行任务"""
        try:
            self.stats["running"] += 1
            
            # 判断是否为协程函数
            if asyncio.iscoroutinefunction(task.func):
                # 异步执行
                if task.timeout:
                    task.result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    task.result = await task.func(*task.args, **task.kwargs)
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                task.result = await loop.run_in_executor(
                    self.thread_pool,
                    task.func,
                    *task.args
                )
                
            # 标记完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            self.completed_tasks.add(task.id)
            
            self.stats["completed"] += 1
            self.stats["running"] -= 1
            
            logger.debug(f"任务完成: {task.name} (耗时: {task.completed_at - task.started_at:.2f}s)")
            
        except asyncio.TimeoutError:
            await self._handle_task_failure(task, TaskException("任务执行超时"))
        except Exception as e:
            await self._handle_task_failure(task, e)
            
    async def _handle_task_failure(self, task: Task, error: Exception):
        """处理任务失败"""
        task.error = error
        task.retry_count += 1
        
        if task.retry_count < task.max_retries:
            # 重试
            task.status = TaskStatus.RETRYING
            self.stats["retrying"] += 1
            
            # 延迟后重新入队
            await asyncio.sleep(2 ** task.retry_count)  # 指数退避
            
            async with self.queue_lock:
                task.status = TaskStatus.PENDING
                heapq.heappush(self.task_queue, task)
                
            logger.warning(f"任务重试 {task.retry_count}/{task.max_retries}: {task.name}")
        else:
            # 最终失败
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            
            self.stats["failed"] += 1
            self.stats["running"] -= 1
            
            logger.error(f"任务失败: {task.name} - {error}")
            
    async def _scheduled_task_checker(self):
        """定时任务检查器"""
        while self.is_running:
            try:
                now = datetime.now()
                
                for task_id, config in list(self.scheduled_tasks.items()):
                    if config["next_run"] <= now:
                        # 提交任务
                        await self.submit_task(
                            config["func"],
                            *config["args"],
                            name=f"scheduled-{config['name']}",
                            priority=TaskPriority.NORMAL,
                            **config["kwargs"]
                        )
                        
                        # 更新下次运行时间
                        config["last_run"] = now
                        config["next_run"] = now + config["interval"]
                        
                await asyncio.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                logger.error(f"定时任务检查错误: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            "submitted": self.stats["submitted"],
            "completed": self.stats["completed"],
            "failed": self.stats["failed"],
            "cancelled": self.stats["cancelled"],
            "retrying": self.stats["retrying"],
            "running": self.stats["running"],
            "pending": len([t for t in self.task_queue if t.status == TaskStatus.PENDING]),
            "queue_size": len(self.task_queue),
            "workers": self.max_workers,
            "scheduled_tasks": len(self.scheduled_tasks)
        }


# 创建全局任务调度器
task_scheduler = TaskScheduler()