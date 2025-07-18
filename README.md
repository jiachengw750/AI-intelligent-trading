# AI智能交易大脑 🤖💹

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![AI Models](https://img.shields.io/badge/AI-DeepSeek%20%7C%20Qwen-orange.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

一个基于先进AI模型的智能加密货币交易系统，集成了DeepSeek和通义千问(Qwen)大语言模型，实现智能市场分析、风险控制和自动化交易。

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [核心技术](#-核心技术原理) • [监控运维](#-监控和运维) • [贡献指南](#-贡献指南)

</div>

## 🚀 功能特性

### 🧠 AI驱动的智能交易
- **双模型架构**: 集成DeepSeek-V3和通义千问QwenLong-L1-32B，实现多模型验证和决策融合
- **智能市场分析**: 基于深度学习的市场趋势预测、情绪分析和模式识别
- **自适应策略**: 根据市场条件自动调整交易策略和参数
- **防幻觉机制**: 多层验证系统，确保AI决策的准确性和可靠性

### 💼 全面的交易功能
- **多交易所支持**: 支持币安等主流交易所，易于扩展
- **高级订单类型**: 市价单、限价单、止损单、冰山订单、TWAP、VWAP等
- **投资组合管理**: 实时持仓管理、自动再平衡、风险分散
- **智能执行**: 最优执行算法，减少滑点和市场冲击

### ⚡ 高性能架构
- **全异步设计**: 基于AsyncIO的高并发处理能力
- **分布式缓存**: Redis缓存层，毫秒级响应
- **智能负载均衡**: 自动分配计算资源，优化系统性能
- **实时数据流**: WebSocket实时推送，零延迟数据传输

### 🛡️ 企业级风控
- **多维度风控**: VaR、CVaR、最大回撤、夏普比率等全方位风险指标
- **实时监控**: 24/7系统监控，异常自动告警
- **智能止损**: AI驱动的动态止损策略
- **合规管理**: 完整的审计日志和合规报告

### 📊 数据与分析
- **实时数据采集**: 市场数据、新闻、社交媒体情绪等多源数据
- **高级数据处理**: 数据清洗、标准化、特征工程
- **向量数据库**: ChromaDB存储，支持语义搜索
- **可视化分析**: Grafana仪表板，实时监控系统状态

## 🛠️ 技术栈

<table>
<tr>
<td>

### 后端技术
- **语言**: Python 3.9+
- **框架**: FastAPI
- **异步**: AsyncIO
- **ORM**: SQLAlchemy
- **任务队列**: Celery

</td>
<td>

### AI/ML
- **LLM**: DeepSeek-V3, Qwen
- **API**: SiliconFlow
- **向量库**: ChromaDB
- **框架**: LangChain

</td>
<td>

### 基础设施
- **数据库**: PostgreSQL
- **缓存**: Redis
- **消息队列**: RabbitMQ
- **容器**: Docker
- **编排**: Kubernetes

</td>
<td>

### 监控运维
- **指标**: Prometheus
- **可视化**: Grafana
- **日志**: ELK Stack
- **追踪**: Jaeger
- **告警**: AlertManager

</td>
</tr>
</table>

## 📁 项目结构

```
AI智能大脑/
├── src/                     # 源代码目录
│   ├── ai/                 # AI模块
│   │   ├── models/        # AI模型接口（DeepSeek、Qwen）
│   │   └── reasoning/     # 推理引擎（包含知识管理和学习功能）
│   ├── core/              # 核心模块
│   │   ├── engine/       # 交易引擎
│   │   └── middleware/   # 中间件
│   ├── trading/           # 交易系统
│   │   ├── execution/    # 订单执行
│   │   ├── portfolio/    # 投资组合管理
│   │   └── exchanges/    # 交易所接口
│   ├── risk/              # 风险管理
│   │   └── control/      # 风控策略
│   ├── data/              # 数据处理
│   │   ├── collectors/   # 数据采集
│   │   └── processors/   # 数据处理
│   ├── monitoring/        # 监控系统
│   │   ├── performance/  # 性能监控
│   │   └── alerts/       # 告警系统
│   ├── api/               # RESTful API
│   │   ├── endpoints/    # API端点
│   │   └── websocket/    # WebSocket接口
│   └── utils/             # 工具函数
├── tests/                  # 测试套件
├── docs/                   # 项目文档
├── scripts/                # 部署脚本
├── docker/                 # Docker配置
├── config.py              # 配置文件
└── main.py                # 程序入口
```

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Docker & Docker Compose
- PostgreSQL 13+
- Redis 6+

### 1. 克隆项目
```bash
git clone https://github.com/your-username/ai-trading-brain.git
cd ai-trading-brain
```

### 2. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下必要参数：
```env
# AI模型配置
SILICONFLOW_API_KEY=your_api_key_here
AI_PRIMARY_MODEL=Tongyi-Zhiwen/QwenLong-L1-32B
AI_SECONDARY_MODEL=deepseek-ai/DeepSeek-V3

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_db
DB_USER=postgres
DB_PASSWORD=your_password

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 交易所API（可选，用于实盘交易）
BINANCE_API_KEY=your_binance_key
BINANCE_SECRET_KEY=your_binance_secret
```

### 3. 使用Docker Compose启动

#### 开发环境
```bash
# 启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

#### 生产环境
```bash
# 使用部署脚本
./scripts/deploy.sh production deploy

# 或使用docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### 4. 访问服务
- **API文档**: http://localhost:8000/docs
- **监控面板**: http://localhost:3000 (Grafana)
- **健康检查**: http://localhost:8000/health

### 5. 运行示例

#### 模拟交易
```bash
# 启动模拟交易
python main.py --mode simulation

# 指定交易对
python main.py --mode simulation --symbols BTC/USDT,ETH/USDT
```

#### API调用示例
```python
import requests

# 获取系统状态
response = requests.get("http://localhost:8000/api/system/status")
print(response.json())

# 获取市场分析
data = {
    "symbol": "BTC/USDT",
    "interval": "1h"
}
response = requests.post("http://localhost:8000/api/analysis/market", json=data)
print(response.json())
```

## 🧪 测试

### 运行完整测试套件
```bash
# 使用Docker
docker-compose -f docker-compose.dev.yml run --rm test

# 本地运行
python -m pytest tests/ -v --cov=src
```

### 运行特定测试
```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 性能测试
pytest tests/integration/test_performance.py -v
```

## 📊 监控和运维

### 系统监控
- **Grafana仪表板**: 实时系统指标、交易统计、性能分析
- **Prometheus指标**: CPU、内存、网络、API延迟等
- **自定义告警**: 交易异常、系统故障、风险超限等

### 日志管理
```bash
# 查看实时日志
tail -f logs/trading_*.log

# 查看错误日志
grep ERROR logs/*.log

# 使用监控脚本
./scripts/monitor.sh production --watch
```

## 🔧 配置说明

### AI模型配置
系统使用SiliconFlow API接入DeepSeek和Qwen模型：

```python
# config.py
@dataclass
class AIConfig:
    # API配置
    SILICONFLOW_API_URL: str = "https://api.siliconflow.cn/v1/chat/completions"
    PRIMARY_MODEL: str = "Tongyi-Zhiwen/QwenLong-L1-32B"  # 主模型
    SECONDARY_MODEL: str = "deepseek-ai/DeepSeek-V3"      # 备用模型
    
    # 推理参数
    TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 4000
    TOP_P: float = 0.9
```

### 交易参数配置
```python
@dataclass
class TradingConfig:
    # 风控参数
    MAX_POSITION_SIZE: float = 0.1  # 单个仓位最大10%
    MAX_DRAWDOWN: float = 0.2       # 最大回撤20%
    STOP_LOSS_PERCENT: float = 0.05 # 止损5%
    
    # 执行参数
    SLIPPAGE_TOLERANCE: float = 0.002  # 滑点容忍度0.2%
    ORDER_TIMEOUT: int = 30            # 订单超时30秒
```

## 🧠 核心技术原理

### 📚 智能知识库系统
我们的知识库系统采用分层存储和语义检索架构，结合向量数据库和传统数据库的优势：

**知识分层架构**：
- **实时层**: 存储最新的市场动态、交易信号和即时分析结果
- **历史层**: 保存历史交易数据、市场模式和策略表现记录
- **规则层**: 维护交易规则、风控策略和合规要求
- **经验层**: 积累交易经验、失败案例和成功模式

**语义检索机制**：
- 使用ChromaDB向量数据库存储知识嵌入
- 支持自然语言查询和语义相似度匹配
- 实现知识的自动关联和推荐
- 动态更新知识权重和相关性评分

### 🎯 连续思维推理框架
基于Chain-of-Thought（CoT）思维链技术，实现多步骤推理和决策验证：

**多步骤推理过程**：
1. **问题分解**: 将复杂的交易决策分解为多个子问题
2. **逐步分析**: 对每个子问题进行深入分析和推理
3. **中间验证**: 在每个推理步骤后进行逻辑检查和验证
4. **结论汇总**: 综合所有推理步骤得出最终决策

**推理路径追踪**：
- 记录完整的推理过程和决策路径
- 支持推理步骤的回溯和调试
- 实现推理结果的可解释性和可审计性
- 建立推理质量评估和优化机制

### 🧬 分层记忆框架
模拟人类记忆系统，构建多层次的记忆存储和检索机制：

**记忆层次结构**：
- **感知记忆**: 存储原始市场数据和实时信息，保持时间短暂
- **短期记忆**: 保存当前交易会话的上下文和临时分析结果
- **长期记忆**: 存储重要的市场模式、交易经验和策略知识
- **元记忆**: 管理记忆的优先级、重要性和遗忘机制

**记忆管理策略**：
- **重要性评估**: 根据交易结果和影响程度评估记忆重要性
- **遗忘机制**: 自动清理过时和无效的记忆内容
- **记忆巩固**: 将频繁使用的短期记忆转化为长期记忆
- **联想检索**: 基于上下文和关联性进行记忆检索

### 🛡️ 幻觉对抗系统
专门设计的多层验证机制，有效防止AI模型的幻觉问题：

**多模型交叉验证**：
- 使用DeepSeek-V3和Qwen双模型并行推理
- 对比不同模型的输出结果，识别异常和不一致
- 实现模型间的相互验证和纠错机制
- 建立模型可信度评估和权重调整

**逻辑一致性检查**：
- **数值合理性**: 验证数值计算的准确性和合理性
- **逻辑连贯性**: 检查推理过程的逻辑连贯性和一致性
- **历史一致性**: 对比历史数据和经验，识别异常结论
- **常识检验**: 基于金融常识和交易规则进行合理性验证

**置信度评估机制**：
- 为每个AI输出分配置信度分数
- 建立置信度阈值和决策门槛
- 实现不确定性量化和风险评估
- 支持人工干预和决策覆盖

### 🔄 伪强化学习机制
结合强化学习思想，在无需真实奖励信号的情况下实现策略优化：

**虚拟奖励设计**：
- **收益奖励**: 基于模拟交易的盈亏情况设计奖励函数
- **风险惩罚**: 对高风险行为和策略失误进行惩罚
- **一致性奖励**: 奖励与历史成功模式一致的决策
- **探索奖励**: 鼓励在安全范围内的策略探索和创新

**策略优化过程**：
1. **行为采样**: 生成多种可能的交易策略和决策方案
2. **虚拟评估**: 使用历史数据和模拟环境评估策略效果
3. **策略排序**: 根据虚拟奖励对策略进行排序和筛选
4. **参数更新**: 调整模型参数以偏向高奖励策略

**自适应学习机制**：
- **在线学习**: 根据实时交易结果调整策略参数
- **增量更新**: 基于新的市场数据和交易经验更新模型
- **忘记机制**: 逐步淡化过时的策略和经验
- **多策略融合**: 结合多种优化策略的优势

### 🔧 技术实现细节

**知识库技术栈**：
- ChromaDB向量数据库用于语义检索
- PostgreSQL关系数据库用于结构化数据
- Redis缓存用于高频访问数据
- 自定义索引和检索算法

**推理引擎架构**：
- 基于有向无环图(DAG)的推理流程
- 支持并行推理和分布式计算
- 实现推理结果的缓存和复用
- 提供推理过程的可视化和调试工具

**学习系统设计**：
- 模块化的学习组件设计
- 支持多种学习算法的插件式集成
- 实现学习过程的监控和调优
- 提供学习效果的评估和报告

### 📊 技术架构流程

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   市场数据源     │    │   新闻数据源     │    │  社交媒体数据   │
│   - 实时行情     │    │   - 财经新闻     │    │  - 投资者情绪   │
│   - 历史数据     │    │   - 公告信息     │    │  - 社群讨论     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   数据采集层     │
                    │  - 数据清洗     │
                    │  - 格式标准化   │
                    │  - 质量检查     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   知识库系统     │
                    │  - 分层存储     │
                    │  - 语义检索     │
                    │  - 动态更新     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   连续思维推理   │
                    │  - 问题分解     │
                    │  - 逐步分析     │
                    │  - 中间验证     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   幻觉对抗系统   │
                    │  - 多模型验证   │
                    │  - 逻辑检查     │
                    │  - 置信度评估   │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   决策融合层     │
                    │  - 多模型聚合   │
                    │  - 权重调整     │
                    │  - 最终决策     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   风险控制层     │
                    │  - 风险评估     │
                    │  - 仓位控制     │
                    │  - 止损策略     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   交易执行层     │
                    │  - 订单生成     │
                    │  - 智能执行     │
                    │  - 状态监控     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   分层记忆系统   │
                    │  - 经验积累     │
                    │  - 模式学习     │
                    │  - 策略优化     │
                    └─────────────────┘
```

## 🛡️ 安全性

### 数据安全
- **加密存储**: 敏感数据使用AES-256加密
- **访问控制**: 基于角色的权限管理(RBAC)
- **审计日志**: 完整的操作审计追踪

### API安全
- **JWT认证**: 安全的令牌认证机制
- **限流保护**: 防止API滥用
- **输入验证**: 严格的参数验证

### AI安全
- **幻觉检测**: 多层验证机制防止AI幻觉
- **决策审计**: 完整的AI决策过程记录
- **人工干预**: 支持人工审查和决策覆盖
- **风险熔断**: 异常情况下的自动保护机制

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献
1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发规范
- 遵循PEP 8编码规范
- 编写完整的文档字符串
- 添加单元测试
- 使用类型注解

## 📄 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。

## 🙏 致谢

感谢以下项目和组织：
- [DeepSeek](https://www.deepseek.com/) - 提供强大的AI模型
- [阿里云](https://www.aliyun.com/) - 通义千问模型
- [SiliconFlow](https://siliconflow.cn/) - AI模型API服务
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Web框架
- 所有贡献者和支持者

## ⚠️ 风险提示

**重要提醒**：
- 加密货币交易具有高风险性，可能导致资金损失
- 本系统仅供学习和研究使用
- 使用前请充分了解相关风险
- 开发者不对使用本系统造成的任何损失负责

## 📞 联系方式

- 📧 邮箱: mailplus1103@163.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/ai-trading-brain/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/your-username/ai-trading-brain/discussions)

---

<div align="center">
Made with ❤️ by AI Trading Brain Team
</div>