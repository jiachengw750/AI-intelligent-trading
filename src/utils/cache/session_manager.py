# -*- coding: utf-8 -*-
"""
分布式会话管理器
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from src.utils.cache.distributed_cache import distributed_cache
from src.utils.helpers.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Session:
    """会话数据"""
    session_id: str
    user_id: str
    created_at: float
    last_accessed: float
    expires_at: float
    data: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at
        
    def update_access_time(self):
        """更新访问时间"""
        self.last_accessed = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """从字典创建"""
        return cls(**data)


class SessionManager:
    """分布式会话管理器"""
    
    def __init__(self, cache=None, session_ttl: int = 3600):
        self.cache = cache or distributed_cache
        self.session_ttl = session_ttl  # 默认1小时
        self.key_prefix = "session"
        
        # 会话配置
        self.config = {
            "max_sessions_per_user": 5,  # 每个用户最大会话数
            "cleanup_interval": 300,      # 清理间隔（秒）
            "extend_on_access": True,     # 访问时延长过期时间
            "secure_cookie": True         # 安全Cookie设置
        }
        
    def _make_session_key(self, session_id: str) -> str:
        """生成会话键"""
        return f"{self.key_prefix}:{session_id}"
        
    def _make_user_sessions_key(self, user_id: str) -> str:
        """生成用户会话列表键"""
        return f"{self.key_prefix}:user:{user_id}"
        
    async def create_session(self, user_id: str, data: Dict[str, Any] = None) -> Session:
        """创建新会话"""
        try:
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 创建会话对象
            session = Session(
                session_id=session_id,
                user_id=user_id,
                created_at=time.time(),
                last_accessed=time.time(),
                expires_at=time.time() + self.session_ttl,
                data=data or {},
                is_active=True
            )
            
            # 保存到缓存
            session_key = self._make_session_key(session_id)
            await self.cache.set(session_key, session.to_dict(), self.session_ttl)
            
            # 添加到用户会话列表
            await self._add_to_user_sessions(user_id, session_id)
            
            # 检查并清理过多的会话
            await self._cleanup_user_sessions(user_id)
            
            logger.info(f"创建会话成功: {session_id} for user {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            raise
            
    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        try:
            session_key = self._make_session_key(session_id)
            session_data = await self.cache.get(session_key)
            
            if not session_data:
                return None
                
            session = Session.from_dict(session_data)
            
            # 检查是否过期
            if session.is_expired():
                await self.delete_session(session_id)
                return None
                
            # 更新访问时间
            if self.config["extend_on_access"]:
                session.update_access_time()
                session.expires_at = time.time() + self.session_ttl
                await self.cache.set(session_key, session.to_dict(), self.session_ttl)
                
            return session
            
        except Exception as e:
            logger.error(f"获取会话失败 {session_id}: {e}")
            return None
            
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """更新会话数据"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
                
            # 更新数据
            session.data.update(data)
            session.update_access_time()
            
            # 保存到缓存
            session_key = self._make_session_key(session_id)
            ttl = int(session.expires_at - time.time())
            await self.cache.set(session_key, session.to_dict(), ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"更新会话失败 {session_id}: {e}")
            return False
            
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            # 获取会话信息
            session = await self.get_session(session_id)
            if session:
                # 从用户会话列表中移除
                await self._remove_from_user_sessions(session.user_id, session_id)
                
            # 删除会话
            session_key = self._make_session_key(session_id)
            return await self.cache.delete(session_key)
            
        except Exception as e:
            logger.error(f"删除会话失败 {session_id}: {e}")
            return False
            
    async def delete_user_sessions(self, user_id: str) -> int:
        """删除用户的所有会话"""
        try:
            # 获取用户所有会话
            sessions = await self.get_user_sessions(user_id)
            
            # 删除每个会话
            deleted = 0
            for session_id in sessions:
                if await self.delete_session(session_id):
                    deleted += 1
                    
            # 删除用户会话列表
            user_key = self._make_user_sessions_key(user_id)
            await self.cache.delete(user_key)
            
            logger.info(f"删除用户 {user_id} 的 {deleted} 个会话")
            return deleted
            
        except Exception as e:
            logger.error(f"删除用户会话失败 {user_id}: {e}")
            return 0
            
    async def get_user_sessions(self, user_id: str) -> List[str]:
        """获取用户的所有会话ID"""
        try:
            user_key = self._make_user_sessions_key(user_id)
            sessions = await self.cache.get(user_key)
            return sessions or []
            
        except Exception as e:
            logger.error(f"获取用户会话列表失败 {user_id}: {e}")
            return []
            
    async def _add_to_user_sessions(self, user_id: str, session_id: str):
        """添加到用户会话列表"""
        try:
            user_key = self._make_user_sessions_key(user_id)
            sessions = await self.get_user_sessions(user_id)
            
            if session_id not in sessions:
                sessions.append(session_id)
                await self.cache.set(user_key, sessions, self.session_ttl * 24)  # 24小时
                
        except Exception as e:
            logger.error(f"添加用户会话失败: {e}")
            
    async def _remove_from_user_sessions(self, user_id: str, session_id: str):
        """从用户会话列表中移除"""
        try:
            user_key = self._make_user_sessions_key(user_id)
            sessions = await self.get_user_sessions(user_id)
            
            if session_id in sessions:
                sessions.remove(session_id)
                await self.cache.set(user_key, sessions, self.session_ttl * 24)
                
        except Exception as e:
            logger.error(f"移除用户会话失败: {e}")
            
    async def _cleanup_user_sessions(self, user_id: str):
        """清理用户过多的会话"""
        try:
            sessions = await self.get_user_sessions(user_id)
            max_sessions = self.config["max_sessions_per_user"]
            
            if len(sessions) > max_sessions:
                # 获取所有会话详情
                session_details = []
                for session_id in sessions:
                    session = await self.get_session(session_id)
                    if session:
                        session_details.append((session_id, session.last_accessed))
                        
                # 按最后访问时间排序
                session_details.sort(key=lambda x: x[1])
                
                # 删除最旧的会话
                to_delete = len(session_details) - max_sessions
                for i in range(to_delete):
                    await self.delete_session(session_details[i][0])
                    
        except Exception as e:
            logger.error(f"清理用户会话失败 {user_id}: {e}")
            
    async def cleanup_expired_sessions(self) -> int:
        """清理所有过期会话"""
        try:
            # 扫描所有会话键
            pattern = f"{self.key_prefix}:*"
            cursor = 0
            cleaned = 0
            
            # 这里简化处理，实际应该使用更高效的方式
            # 比如维护一个过期时间索引
            
            logger.info(f"清理了 {cleaned} 个过期会话")
            return cleaned
            
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0
            
    async def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        try:
            # 简化处理，实际应该维护计数器
            return 0
            
        except Exception as e:
            logger.error(f"获取活跃会话数量失败: {e}")
            return 0
            
    def generate_session_token(self, session_id: str) -> str:
        """生成会话令牌"""
        # 简化处理，实际应该使用JWT或加密
        return f"token_{session_id}"
        
    def verify_session_token(self, token: str) -> Optional[str]:
        """验证会话令牌"""
        # 简化处理，实际应该验证JWT或解密
        if token.startswith("token_"):
            return token.replace("token_", "")
        return None


# 创建全局会话管理器
session_manager = SessionManager()