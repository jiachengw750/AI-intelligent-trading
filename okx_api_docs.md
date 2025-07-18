# OKX API 文档

## 概览

欢迎查看 API 文档。我们提供完整的REST和WebSocket API以满足您的交易需求。

- 在 my.okx.com 完成注册的用户，请访问 [https://my.okx.com/docs-v5/zh/](https://my.okx.com/docs-v5/zh/) 获取 API 文档。
- 在 app.okx.com 完成注册的用户，请访问 [https://app.okx.com/docs-v5/zh/](https://app.okx.com/docs-v5/zh/) 获取 API 文档。

## API学习资源与技术支持

### 教程

- 学习使用 API 交易: [API 使用指南](/docs-v5/trick_zh/#instrument-configuration)
- 学习使用Python交易现货: [Python 现货交易教程](/help/how-can-i-do-spot-trading-with-the-jupyter-notebook)
- 学习使用Python交易衍生品: [Python 衍生品交易教程](/help/how-can-i-do-derivatives-trading-with-the-jupyter-notebook)

### Python包

- 使用Python SDK更简单地上手: [Python SDK](https://pypi.org/project/python-okx/)
- 轻松上手Python做市商代码 [Python 做市商代码示例](https://github.com/okxapi/okx-sample-market-maker)

### 客户服务

- 如有问题请咨询线上客服

## 创建我的APIKey

点击跳转至官网创建V5APIKey的页面 [创建我的APIKey](/account/my-api)

### 生成APIKey

在对任何请求进行签名之前，您必须通过交易网站创建一个APIKey。创建APIKey后，您将获得3个必须记住的信息：

- APIKey
- SecretKey
- Passphrase

APIKey和SecretKey将由平台随机生成和提供，Passphrase将由您提供以确保API访问的安全性。平台将存储Passphrase加密后的哈希值进行验证，但如果您忘记Passphrase，则无法恢复，请您通过交易网站重新生成新的APIKey。

### APIKey 权限

APIKey 有如下3种权限，一个 APIKey 可以有一个或多个权限。

- 读取：查询账单和历史记录等 读权限
- 提现：可以进行提币
- 交易：可以下单和撤单，转账，调整配置 等写权限

### APIKey 安全性

为了提高安全性，我们建议您将 APIKey 绑定 IP

- 每个APIKey最多可绑定20个IP地址，IP地址支持IPv4/IPv6和网段的格式。

未绑定IP且拥有交易或提币权限的APIKey，将在闲置14天之后自动删除。(模拟盘的 API key 不会被删除)

- 用户调用了需要 APIKey 鉴权的接口，才会被视为 APIKey 被使用。
- 调用了不需要 APIKey 鉴权的接口，即使传入了 APIKey的信息，也不会被视为使用过。
- Websocket 只有在登陆的时候，才会被视为 APIKey 被使用过。在登陆后的连接中做任何操作（如 订阅/下单），也不会被认为 APIKey 被使用，这点需要注意。

用户可以在 [安全中心](/zh-hans/account/security) 中看到未绑定IP且拥有交易/提现权限的 APIKey 最近使用记录。

## REST 请求验证

### 发起请求

所有REST私有请求头都必须包含以下内容：

- `OK-ACCESS-KEY`字符串类型的APIKey。
- `OK-ACCESS-SIGN`使用HMAC SHA256哈希函数获得哈希值，再使用Base-64编码（请参阅签名）。
- `OK-ACCESS-TIMESTAMP`发起请求的时间（UTC），如：2020-12-08T09:08:57.715Z
- `OK-ACCESS-PASSPHRASE`您在创建API密钥时指定的Passphrase。

所有请求都应该含有application/json类型内容，并且是有效的JSON。

### 签名

`OK-ACCESS-SIGN`的请求头是对`timestamp + method + requestPath + body`字符串（+表示字符串连接），以及SecretKey，使用HMAC SHA256方法加密，通过Base-64编码输出而得到的。

如：`sign=CryptoJS.enc.Base64.stringify(CryptoJS.HmacSHA256(timestamp + 'GET' + '/api/v5/account/balance?ccy=BTC', SecretKey))`

其中，`timestamp`的值与`OK-ACCESS-TIMESTAMP`请求头相同，为ISO格式，如`2020-12-08T09:08:57.715Z`。

method是请求方法，字母全部大写：`GET/POST`。

requestPath是请求接口路径。如：`/api/v5/account/balance`

body是指请求主体的字符串，如果请求没有主体（通常为GET请求）则body可省略。如：`{"instId":"BTC-USDT","lever":"5","mgnMode":"isolated"}`

GET请求参数是算作requestPath，不算body

SecretKey为用户申请APIKey时所生成。如：`22582BD0CFF14C41EDBF1AB98506286D`

## WebSocket

### 概述

WebSocket是HTML5一种新的协议（Protocol）。它实现了用户端与服务器全双工通信， 使得数据可以快速地双向传播。通过一次简单的握手就可以建立用户端和服务器连接， 服务器根据业务规则可以主动推送信息给用户端。其优点如下：

- 用户端和服务器进行数据传输时，请求头信息比较小，大概2个字节。
- 用户端和服务器皆可以主动地发送数据给对方。
- 不需要多次创建TCP请求和销毁，节约宽带和服务器的资源。

强烈建议开发者使用WebSocket API获取市场行情和买卖深度等信息。

### 连接

**连接限制**：3 次/秒 (基于IP)

当订阅公有频道时，使用公有服务的地址；当订阅私有频道时，使用私有服务的地址

**请求限制**：

每个连接 对于 `订阅`/`取消订阅`/`登录` 请求的总次数限制为 480 次/小时

如果出现网络问题，系统会自动断开连接

如果连接成功后30s未订阅或订阅后30s内服务器未向用户推送数据，系统会自动断开连接

为了保持连接有效且稳定，建议您进行以下操作：

1. 每次接收到消息后，用户设置一个定时器，定时N秒，N 小于30。
2. 如果定时器被触发（N 秒内没有收到新消息），发送字符串 'ping'。
3. 期待一个文字字符串'pong'作为回应。如果在 N秒内未收到，请发出错误或重新连接。

### 连接限制

子账户维度，订阅每个 WebSocket 频道的最大连接数为 30 个。每个 WebSocket 连接都由唯一的 connId 标识。

受此限制的 WebSocket 频道如下：

1. 订单频道
2. 账户频道
3. 持仓频道
4. 账户余额和持仓频道
5. 爆仓风险预警推送频道
6. 账户greeks频道

若用户通过不同的请求参数在同一个 WebSocket 连接下订阅同一个频道，如使用 `{"channel": "orders", "instType": "ANY"}` 和 `{"channel": "orders", "instType": "SWAP"}`，只算为一次连接。

新链接订阅频道时，平台将对该订阅返回`channel-conn-count`的消息同步链接数量。

当超出限制时，一般最新订阅的链接会收到拒绝。用户会先收到平时的订阅成功信息然后收到`channel-conn-count-error`消息，代表平台终止了这个链接的订阅。

通过 WebSocket 进行的订单操作，例如下单、修改和取消订单，不会受到此改动影响。

### 登录

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| op | String | 是 | 操作，`login` |
| args | Array of objects | 是 | 账户列表 |
| > apiKey | String | 是 | APIKey |
| > passphrase | String | 是 | APIKey 的密码 |
| > timestamp | String | 是 | 时间戳，Unix Epoch时间，单位是秒 |
| > sign | String | 是 | 签名字符串 |

#### 返回参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| event | String | 是 | 操作，`login` `error` |
| code | String | 否 | 错误码 |
| msg | String | 否 | 错误消息 |
| connId | String | 是 | WebSocket连接ID |

**apiKey**: 调用API的唯一标识。需要用户手动设置一个
**passphrase**: APIKey的密码
**timestamp**: Unix Epoch 时间戳，单位为秒，如 1704876947
**sign**: 签名字符串，签名算法如下：

先将`timestamp` 、 `method` 、`requestPath` 进行字符串拼接，再使用HMAC SHA256方法将拼接后的字符串和SecretKey加密，然后进行Base64编码

**SecretKey**: 用户申请APIKey时所生成的安全密钥，如：22582BD0CFF14C41EDBF1AB98506286D

**其中 timestamp 示例**: const timestamp = '' + Date.now() / 1,000

**其中 sign 示例**: sign=CryptoJS.enc.Base64.stringify(CryptoJS.HmacSHA256(timestamp +'GET'+ '/users/self/verify', secret))

**method** 总是 'GET'

**requestPath** 总是 '/users/self/verify'

请求在时间戳之后30秒会失效，如果您的服务器时间和API服务器时间有偏差，推荐使用 REST API查询API服务器的时间，然后设置时间戳

### 订阅

WebSocket 频道分成两类： `公共频道` 和 `私有频道`

`公共频道`无需登录，包括行情频道，K线频道，交易数据频道，资金费率频道，限价范围频道，深度数据频道，标记价格频道等。

`私有频道`需登录，包括用户账户频道，用户交易频道，用户持仓频道等。

用户可以选择订阅一个或者多个频道，多个频道总长度不能超过 64 KB。

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| op | String | 是 | 操作，`subscribe` |
| args | Array of objects | 是 | 请求订阅的频道列表 |
| > channel | String | 是 | 频道名 |
| > instType | String | 否 | 产品类型 `SPOT`：币币 `MARGIN`：币币杠杆 `SWAP`：永续 `FUTURES`：交割 `OPTION`：期权 `ANY`：全部 |
| > instFamily | String | 否 | 交易品种 适用于`交割`/`永续`/`期权` |
| > instId | String | 否 | 产品ID |

#### 返回参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| event | String | 是 | 事件，`subscribe` `error` |
| arg | Object | 否 | 订阅的频道 |
| > channel | String | 是 | 频道名 |
| > instType | String | 否 | 产品类型 |
| > instFamily | String | 否 | 交易品种 |
| > instId | String | 否 | 产品ID |
| code | String | 否 | 错误码 |
| msg | String | 否 | 错误消息 |
| connId | String | 是 | WebSocket连接ID |

### 取消订阅

可以取消一个或者多个频道

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| op | String | 是 | 操作，`unsubscribe` |
| args | Array of objects | 是 | 取消订阅的频道列表 |
| > channel | String | 是 | 频道名 |
| > instType | String | 否 | 产品类型 |
| > instFamily | String | 否 | 交易品种 |
| > instId | String | 否 | 产品ID |

#### 返回参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| event | String | 是 | 事件，`unsubscribe` `error` |
| arg | Object | 否 | 取消订阅的频道 |
| code | String | 否 | 错误码 |
| msg | String | 否 | 错误消息 |
| connId | String | 是 | WebSocket连接ID |

### 通知

WebSocket有一种消息类型(event=`notice`)。

用户会在如下场景收到此类信息：

- Websocket服务升级断线

在推送服务升级前60秒会推送信息，告知用户WebSocket服务即将升级。用户可以重新建立新的连接避免由于断线造成的影响。

目前支持WebSocket公共频道(/ws/v5/public)和私有频道(/ws/v5/private)。

## 账户模式

为了方便您的交易体验，请在开始交易前设置适当的账户模式。

交易账户交易系统提供四个账户模式，分别为`现货模式`、`合约模式`、`跨币种保证金模式`以及`组合保证金模式`。

账户模式的首次设置，需要在网页或手机app上进行。

## 实盘交易

实盘API交易地址如下：

- REST：`https://www.okx.com`
- WebSocket公共频道：`wss://ws.okx.com:8443/ws/v5/public`
- WebSocket私有频道：`wss://ws.okx.com:8443/ws/v5/private`
- WebSocket业务频道：`wss://ws.okx.com:8443/ws/v5/business`

## 模拟盘交易

目前可以进行 API 的模拟盘交易，部分功能不支持如`提币`、`充值`、`申购赎回`等。

模拟盘API交易地址如下：

- REST：`https://www.okx.com`
- WebSocket公共频道：`wss://wspap.okx.com:8443/ws/v5/public`
- WebSocket私有频道：`wss://wspap.okx.com:8443/ws/v5/private`
- WebSocket业务频道：`wss://wspap.okx.com:8443/ws/v5/business`

模拟盘的账户与欧易的账户是互通的，如果您已经有欧易账户，可以直接登录。

模拟盘API交易需要在模拟盘上创建APIKey：

登录欧易账户—>交易—>模拟交易—>个人中心—>创建模拟盘APIKey—>开始模拟交易

注意：模拟盘的请求的header里面需要添加 "x-simulated-trading: 1"。

### 模拟盘交互式浏览器

该功能接口用户需先登录，接口只会请求模拟环境

- Parameters 面板中点击`Try it out`按钮，编辑请求参数。
- 点击`Execute`按钮发送请求。Responses 面板中查看请求结果。

立即体验 [交互式浏览器](/demo-trading-explorer/v5/zh)

## 基本信息

**交易所层面的下单规则如下：**

- 未成交订单（包括 post only，limit和处理中的taker单）的最大挂单数：4,000个
- 单个交易产品未成交订单的最大挂单数为500个，被计入到 500 笔挂单数量限制的**订单类型**包括：
  - 限价委托 (Limit)
  - 市价委托 (Market)
  - 只挂单 (Post only)
  - 全部成交或立即取消 (FOK)
  - 立即成交并取消剩余 (IOC)
  - 市价委托立即成交并取消剩余 (optimal limit IOC)
  - 止盈止损 (TP/SL)
  - 以下类型的订单触发的限价和市价委托：
    - 止盈止损 (TP/SL)
    - 计划委托 (Trigger)
    - 移动止盈止损 (Trailing stop)
    - 套利下单 (Arbitrage)
    - 冰山策略 (Iceberg)
    - 时间加权策略 (TWAP)
    - 定投 (Recurring buy)
- 价差订单最大挂单数：所有价差订单挂单合计500个
- 策略委托订单最大挂单数：
  - 止盈止损：100个 每个Instrument ID
  - 计划委托：500个
  - 移动止盈止损：50个
  - 冰山委托：100个
  - 时间加权委托：20个
- 网格策略最大个数：
  - 现货网格：100个
  - 合约网格：100个

**交易限制规则如下：**

- 当taker订单匹配的maker订单数量超过最大限制1000笔时，taker订单将被取消
  - 限价单仅成交与1000笔maker订单相对应的部分，并取消剩余；
  - 全部成交或立即取消（FOK）订单将直接被取消。

**返回数据规则如下：**

- 当返回数据中，有`code`，且没有`sCode`字段时，`code`和`msg`代表请求结果或者报错原因；
- 当返回中有`sCode`字段时，代表请求结果或者报错原因的是`sCode`和`sMsg`，而不是`code`和`msg`。

**交易品种`instFamily`参数说明：**

- 与uly没有区别：
  - 如："BTC-USD-SWAP"的instFamily和uly均为BTC-USD，"BTC-USDC-SWAP"的instFamily和uly均为为BTC-USDC。
  - 若请求参数指定uly为"BTC-USD"，会包含"BTC-USD"币本位合约的数据
  - 若请求参数指定instFamily为"BTC-USD"，也只会包含"BTC-USD"币本位合约的数据。
- 您可以通过"获取交易产品基础信息"接口获取交易产品对应的instFamily。

## 交易时效性

由于网络延时或者OKX服务器繁忙会导致订单无法及时处理。如果您对交易时效性有较高的要求，可以灵活设置请求有效截止时间`expTime`以达到你的要求。

（批量）下单，（批量）改单接口请求中如果包含`expTime`，如果服务器当前系统时间超过`expTime`，则该请求不会被服务器处理。

### REST API

请求头中设置如下参数

| 参数名 | 类型 | 是否必须 | 描述 |
|--------|------|----------|------|
| expTime | String | 否 | 请求有效截止时间。Unix时间戳的毫秒数格式，如 `1597026383085` |

目前支持如下接口：

- 下单
- 批量下单
- 修改订单
- 批量修改订单

### WebSocket

请求中设置如下参数

| 参数名 | 类型 | 是否必须 | 描述 |
|--------|------|----------|------|
| expTime | String | 否 | 请求有效截止时间。Unix时间戳的毫秒数格式，如 `1597026383085` |

目前支持如下接口：

- 下单
- 批量下单
- 修改订单
- 批量修改订单

## 限速

我们的 REST 和 WebSocket API 使用限速来保护我们的 API 免受恶意使用，因此我们的交易平台可以可靠和公平地运行。

当请求因限速而被我们的系统拒绝时，系统会返回错误代码 50011（用户请求频率过快，超过该接口允许的限额。请参考 API 文档并限制请求）。

每个接口的限速都不同。您可以从接口详细信息中找到每个接口的限制。限速定义详述如下：

- WebSocket 登录和订阅限速基于连接。
- 公共未经身份验证的 REST 限速基于 IP 地址。
- 私有 REST 限速基于 User ID（子帐户具有单独的 User ID）。
- WebSocket 订单管理限速基于 User ID（子账户具有单独的 User ID）。

### 交易相关API

对于与交易相关的 API（下订单、取消订单和修改订单），以下条件适用：

- 限速在 REST 和 WebSocket 通道之间共享。
- 下单、修改订单、取消订单的限速相互独立。
- 限速在 Instrument ID 级别定义（期权除外）
- 期权的限速是根据 Instrument Family 级别定义的。请参阅获取交易产品基础信息接口以查看交易品种信息。
- 批量订单接口和单订单接口的限速也是独立的，除了只有一个订单发送到批量订单接口时，该订单将被视为一个订单并采用单订单限速。

### 子账户限速

子账户维度，每2秒最多允许1000个订单相关请求。仅有新订单及修改订单请求会被计入此限制。此限制涵盖以下所列的所有接口。对于包含多个订单的批量请求，每个订单将被单独计数。如果请求频率超过限制，系统会返回50061错误码。产品ID维度的限速规则保持不变，现有的限速规则与新增的子账户维度限速将并行运行。若用户需要更高的速率限制，可以通过多个子账户进行交易。

### 基于成交比率的子账户限速

仅适用于用户等级 >= VIP5的用户。

为了激励更高效的交易，交易所将为交易成交比率高的用户提供更高的子账户限速。

交易所将在每天 00:00 UTC，根据过去七天的交易数据计算两个比率。

1. 子账户成交比率：该比率为（子账户的USDT对应交易量）/（每个交易产品的新增和修改请求数 * 交易产品乘数之和）。请注意，在这种情况下，母账户自身也被视为一个"子账户"。
2. 母账户合计成交比率：该比率为（母账户层面的USDT对应交易量）/（所有子账户各个交易产品的新增和修改请求数 * 交易产品乘数之和）。

### 最佳实践

如果您需要的请求速率高于我们的限速，您可以设置不同的子账户来批量请求限速。我们建议使用此方法来限制或间隔请求，以最大化每个帐户的限速并避免断开连接或拒绝请求。

## 做市商申请

满足以下任意条件的用户即可申请加入欧易做市商计划：

- 交易等级VIP2及以上
- 其他交易所达标做市商（需审核）

感兴趣的各方可以使用此表格联系我们：[https://okx.typeform.com/contact-sales](https://okx.typeform.com/contact-sales)

为鼓励做市商为平台提供更好的流动性，可以享受更优的交易手续费，同时也承担相应的做市责任。具体做市责任及手续费申请成功后提供相关资料。

欧易保留对做市商项目的最终解释权

做市商项目不支持VIP、交易量相关活动以及任何形式的返佣活动

## 经纪商申请

如果您的业务平台提供数字货币服务，您就可以申请加入欧易经纪商项目，成为欧易的经纪商合作伙伴，享受专属的经纪商服务，并通过用户在欧易产生的交易手续费赚取高额返佣。

经纪商业务包含且不限：聚合交易平台、交易机器人、跟单平台、交易策略提供方、量化策略机构、资管平台等。

- [点击申请](/cn/broker/home)
- [经纪商规则介绍](/cn/help/introduction-of-rules-on-okx-brokers)
- 如有问题请咨询线上客服

具体经纪商业务文档及产品服务在申请成功后提供相关资料。

# 交易账户

`账户`功能模块下的API接口需要身份验证。

## REST API

### 获取交易产品基础信息

获取当前账户可交易产品的信息列表。

#### 限速：20次/2s
#### 限速规则：User ID + Instrument Type
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/instruments`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 `SPOT`：币币 `MARGIN`：币币杠杆 `SWAP`：永续合约 `FUTURES`：交割合约 `OPTION`：期权 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |

### 查看账户余额

获取交易账户中资金余额信息。

#### 限速：10次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/balance`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 币种，如 BTC 支持多币种查询（不超过20个），币种之间半角逗号分隔 |

### 查看持仓信息

获取该账户下拥有实际持仓的信息。账户为买卖模式会显示净持仓（net），账户为开平仓模式下会分别返回开多（long）或开空（short）的仓位。按照仓位创建时间倒序排列。

#### 限速：10次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/positions`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 `MARGIN`：币币杠杆 `SWAP`：永续合约 `FUTURES`：交割合约 `OPTION`：期权 |
| instId | String | 否 | 产品ID，如 BTC-USD-190927-5000-C |
| posId | String | 否 | 持仓ID |

### 查看历史持仓信息

获取最近3个月有更新的仓位信息，按照仓位更新时间倒序排列。

#### 限速：1次/10s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/positions-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 |
| instId | String | 否 | 产品ID |
| mgnMode | String | 否 | 保证金模式 `cross`：全仓 `isolated`：逐仓 |
| type | String | 否 | 持仓类型 `1`：开多 `2`：开空 `3`：净持仓 |
| posId | String | 否 | 持仓ID |
| after | String | 否 | 请求此时间戳之前（更旧的数据）的分页内容，传的值为对应接口的uTime |
| before | String | 否 | 请求此时间戳之后（更新的数据）的分页内容，传的值为对应接口的uTime |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### 查看账户持仓风险

获取账户持仓信息，只有逐仓会有仓位风险，全仓以及其他模式不会有仓位风险。

#### 限速：10次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/account-position-risk`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 |

### 账单流水查询（近七天）

查询账户资产流水数据。流水会有延迟，查询到的数据为上一个小时及之前的数据。

#### 限速：5次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/bills`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 |
| ccy | String | 否 | 账单币种 |
| mgnMode | String | 否 | 保证金模式 |
| ctType | String | 否 | linear：正向合约 inverse：反向合约 仅适用于交割/永续 |
| type | String | 否 | 账单类型 |
| subType | String | 否 | 账单子类型 |
| after | String | 否 | 请求此时间戳之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此时间戳之后（更新的数据）的分页内容 |
| begin | String | 否 | 筛选的开始时间戳，Unix 时间戳为毫秒数格式 |
| end | String | 否 | 筛选的结束时间戳，Unix 时间戳为毫秒数格式 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### 账单流水查询（近一年）

查询账户资产流水数据。流水会有延迟，查询到的数据为上一个小时及之前的数据。

#### 限速：5次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/bills-archive`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 |
| ccy | String | 否 | 账单币种 |
| mgnMode | String | 否 | 保证金模式 |
| ctType | String | 否 | linear：正向合约 inverse：反向合约 |
| type | String | 否 | 账单类型 |
| subType | String | 否 | 账单子类型 |
| after | String | 否 | 请求此时间戳之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此时间戳之后（更新的数据）的分页内容 |
| begin | String | 否 | 筛选的开始时间戳 |
| end | String | 否 | 筛选的结束时间戳 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 查看账户配置

查看当前账户的配置信息。

#### 限速：5次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/config`

### 设置持仓模式

#### 限速：5次/2s
#### 限速规则：User ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/account/set-position-mode`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| posMode | String | 是 | 持仓方式 `long_short_mode`：开平仓模式 `net_mode`：买卖模式 |

### 设置杠杆倍数

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/account/set-leverage`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| lever | String | 是 | 杠杆倍数 |
| mgnMode | String | 是 | 保证金模式 `isolated`：逐仓 `cross`：全仓 |
| instId | String | 可选 | 产品ID |
| ccy | String | 可选 | 保证金币种 |
| posSide | String | 可选 | 持仓方向 `long`：开多 `short`：开空 |

### 获取最大可下单数量

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/max-size`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| tdMode | String | 是 | 交易模式 `cross`：全仓 `isolated`：逐仓 `cash`：非保证金 |
| ccy | String | 否 | 保证金币种 |
| px | String | 否 | 委托价格 |
| leverage | String | 否 | 杠杆倍数 |
| unSpotOffset | Boolean | 否 | true：禁用现货对冲 false：启用现货对冲 |

### 获取最大可用余额/保证金

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/max-avail-size`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| tdMode | String | 是 | 交易模式 |
| ccy | String | 否 | 保证金币种 |
| reduceOnly | Boolean | 否 | 是否为只减仓模式 |
| unSpotOffset | Boolean | 否 | true：禁用现货对冲 false：启用现货对冲 |
| quickMgnType | String | 否 | 一键借币类型 |

### 调整保证金

增加或减少逐仓仓位的保证金。

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/account/position/margin-balance`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| posSide | String | 是 | 持仓方向 |
| type | String | 是 | `add`：增加 `reduce`：减少 |
| amt | String | 是 | 调整保证金数量 |
| ccy | String | 否 | 保证金币种 |
| auto | Boolean | 否 | 是否自动借币 |
| loanTrans | Boolean | 否 | 是否支持跨币种保证金模式或组合保证金模式下的借币转入/转出 |

### 获取杠杆倍数

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/leverage-info`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| mgnMode | String | 是 | 保证金模式 |

### 获取当前账户交易手续费费率

#### 限速：5次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/trade-fee`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| instId | String | 否 | 产品ID |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |

### 获取计息记录

#### 限速：5次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/interest-accrued`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| type | String | 否 | 借币类型 |
| ccy | String | 否 | 借币币种 |
| instId | String | 否 | 产品ID |
| mgnMode | String | 否 | 保证金模式 |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| limit | String | 否 | 分页返回的结果集数量 |

### 获取用户当前市场借币利率

#### 限速：5次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/account/interest-rate`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 币种 |

### 设置账户模式

#### 限速：5次/2s
#### 限速规则：User ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/account/set-account-mode`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| acctMode | String | 是 | 账户模式 `1`：现货模式 `2`：合约模式 `3`：跨币种保证金模式 `4`：组合保证金模式 |

## WebSocket

### 账户频道

#### 频道名：account

获取账户信息数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "account"
        }
    ]
}
```

#### 推送数据参数

| 参数 | 类型 | 描述 |
|------|------|------|
| arg | Object | 订阅的频道 |
| > channel | String | 频道名 |
| data | Array | 账户信息数据 |
| > uTime | String | 账户信息的更新时间 |
| > totalEq | String | 美元层面权益 |
| > isoEq | String | 美元层面逐仓仓位权益 |
| > adjEq | String | 美元层面有效保证金 |
| > ordFroz | String | 美元层面全仓挂单占用保证金 |
| > imr | String | 美元层面占用保证金 |
| > mmr | String | 美元层面维持保证金 |
| > borrowFroz | String | 美元层面潜在借币占用保证金 |
| > mgnRatio | String | 美元层面保证金率 |
| > notionalUsd | String | 美元层面名义价值 |
| > upl | String | 美元层面未实现盈亏 |
| > details | Array | 各币种资产详细信息 |

### 持仓频道

#### 频道名：positions

获取持仓信息数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "positions",
            "instType": "ANY"
        }
    ]
}
```

#### 推送数据参数

| 参数 | 类型 | 描述 |
|------|------|------|
| arg | Object | 订阅的频道 |
| > channel | String | 频道名 |
| > instType | String | 产品类型 |
| data | Array | 持仓信息数据 |
| > posId | String | 持仓ID |
| > tradeId | String | 最新成交ID |
| > instId | String | 产品ID |
| > instType | String | 产品类型 |
| > mgnMode | String | 保证金模式 |
| > posSide | String | 持仓方向 |
| > pos | String | 持仓数量 |
| > baseBal | String | 交易币余额 |
| > quoteBal | String | 计价币余额 |
| > posCcy | String | 持仓币种 |
| > availPos | String | 可平仓数量 |
| > avgPx | String | 开仓平均价 |
| > upl | String | 未实现收益 |
| > uplRatio | String | 未实现收益率 |
| > lever | String | 杠杆倍数 |
| > liqPx | String | 预估强平价 |
| > markPx | String | 最新标记价格 |
| > imr | String | 占用保证金 |
| > margin | String | 保证金余额 |
| > mgnRatio | String | 保证金率 |
| > mmr | String | 维持保证金 |
| > liab | String | 负债额 |
| > liabCcy | String | 负债币种 |
| > interest | String | 利息 |
| > tradeId | String | 最新成交ID |
| > optVal | String | 期权价值 |
| > notionalUsd | String | 以美元价值为单位的持仓数量 |
| > adl | String | 信号区 |
| > ccy | String | 保证金币种 |
| > last | String | 最新成交价 |
| > idxPx | String | 指数价格 |
| > usdPx | String | 美元价格 |
| > bePx | String | 盈亏平衡价 |
| > deltaBS | String | BS delta |
| > deltaPA | String | PA delta |
| > gammaBS | String | BS gamma |
| > gammaPA | String | PA gamma |
| > thetaBS | String | BS theta |
| > thetaPA | String | PA theta |
| > vegaBS | String | BS vega |
| > vegaPA | String | PA vega |
| > realizedPnl | String | 已实现收益 |
| > pTime | String | 持仓创建时间 |
| > uTime | String | 持仓信息更新时间 |
| > cTime | String | 持仓创建时间 |

### 账户余额和持仓频道

#### 频道名：balance_and_position

获取账户余额和持仓信息数据推送。首次订阅会推送账户和持仓的存量数据，后续推送增量数据。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "balance_and_position"
        }
    ]
}
```

### 爆仓风险预警推送频道

#### 频道名：liquidation-warning

获取爆仓风险预警推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "liquidation-warning",
            "instType": "ANY"
        }
    ]
}
```

### 账户greeks频道

#### 频道名：account-greeks

获取账户greeks信息数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "account-greeks",
            "ccy": "BTC"
        }
    ]
}
```

# 撮合交易

## 交易

### POST / 下单

您可以下单、撤单、修改订单。

#### 限速：60次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/order`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID，如 BTC-USDT |
| tdMode | String | 是 | 交易模式 `cash`：非保证金 `cross`：全仓 `isolated`：逐仓 |
| ccy | String | 否 | 保证金币种，仅适用于单币种保证金模式下的全仓杠杆订单 |
| clOrdId | String | 否 | 客户自定义订单ID |
| tag | String | 否 | 订单标签 |
| side | String | 是 | 订单方向 `buy`：买 `sell`：卖 |
| ordType | String | 是 | 订单类型 `market`：市价单 `limit`：限价单 `post_only`：只挂单 `fok`：全部成交或立即取消 `ioc`：立即成交并取消剩余 `optimal_limit_ioc`：市价委托立即成交并取消剩余 |
| sz | String | 是 | 委托数量 |
| px | String | 可选 | 委托价格，仅适用于limit、post_only、fok、ioc类型的订单 |
| reduceOnly | Boolean | 否 | 是否只减仓，true或false，默认false |
| tgtCcy | String | 否 | 市价单委托数量sz的单位 |
| banAmend | Boolean | 否 | 是否禁止币币市价改单，true或false，默认false |
| quickMgnType | String | 否 | 一键借币类型，仅适用于杠杆逐仓的一键借币模式 |
| stpId | String | 否 | 自成交保护ID |
| stpMode | String | 否 | 自成交保护模式 |
| attachAlgoOrds | Array | 否 | 下单附带止盈止损信息 |

### POST / 批量下单

批量下单，每次最多可以下20个订单。

#### 限速：300次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/batch-orders`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| 请求参数为数组类型，数组中的每个元素都是一个订单信息的JSON对象，每个订单信息的参数要求同下单接口 |

### POST / 撤单

撤销之前下的未完成订单。

#### 限速：60次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/cancel-order`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| ordId | String | 可选 | 订单ID |
| clOrdId | String | 可选 | 客户自定义订单ID |

### POST / 批量撤单

批量撤销订单，每次最多可以撤销20个订单。

#### 限速：300次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/cancel-batch-orders`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| 请求参数为数组类型，数组中的每个元素都是一个撤单信息的JSON对象，每个撤单信息的参数要求同撤单接口 |

### POST / 修改订单

修改之前下的未完成订单。

#### 限速：60次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/amend-order`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| cxlOnFail | Boolean | 否 | false：不自动撤单 true：自动撤单 当订单修改失败时，该订单是否需要自动撤销，默认为false |
| ordId | String | 可选 | 订单ID |
| clOrdId | String | 可选 | 客户自定义订单ID |
| reqId | String | 否 | 用户自定义修改事件ID |
| newSz | String | 可选 | 修改的新数量 |
| newPx | String | 可选 | 修改的新价格 |
| newTgtCcy | String | 否 | 新的市价单委托数量sz的单位 |
| attachAlgoOrds | Array | 否 | 下单附带止盈止损时，客户自定义的策略订单ID |

### POST / 批量修改订单

批量修改订单，每次最多可以修改20个订单。

#### 限速：300次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/amend-batch-orders`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| 请求参数为数组类型，数组中的每个元素都是一个修改订单信息的JSON对象，每个修改订单信息的参数要求同修改订单接口 |

### POST / 市价仓位全平

市价全平某个产品的仓位。

#### 限速：20次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/close-position`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| posSide | String | 可选 | 持仓方向 |
| mgnMode | String | 是 | 保证金模式 |
| ccy | String | 否 | 保证金币种 |
| autoCxl | Boolean | 否 | 当市价全平时，平仓单受到风控拦截导致下单失败时，是否关闭仓位上的所有挂单，默认为false |
| clOrdId | String | 否 | 客户自定义订单ID |
| tag | String | 否 | 订单标签 |

### GET / 获取订单信息

获取订单信息

#### 限速：60次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/order`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| ordId | String | 可选 | 订单ID |
| clOrdId | String | 可选 | 客户自定义订单ID |

### GET / 获取未成交订单列表

获取当前账户下所有未成交订单信息

#### 限速：60次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/orders-pending`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |
| ordType | String | 否 | 订单类型 |
| state | String | 否 | 订单状态 |
| after | String | 否 | 请求此ID之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此ID之后（更新的数据）的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### GET / 获取历史订单记录（近七天）

获取最近7天的订单信息，按照订单创建时间倒序排列。

#### 限速：40次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/orders-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |
| ordType | String | 否 | 订单类型 |
| state | String | 否 | 订单状态 |
| category | String | 否 | 订单种类 |
| after | String | 否 | 请求此ID之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此ID之后（更新的数据）的分页内容 |
| begin | String | 否 | 筛选的开始时间戳，Unix 时间戳为毫秒数格式 |
| end | String | 否 | 筛选的结束时间戳，Unix 时间戳为毫秒数格式 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### GET / 获取历史订单记录（近三个月）

获取最近3个月的订单信息，按照订单创建时间倒序排列。

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/orders-history-archive`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |
| ordType | String | 否 | 订单类型 |
| state | String | 否 | 订单状态 |
| category | String | 否 | 订单种类 |
| after | String | 否 | 请求此ID之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此ID之后（更新的数据）的分页内容 |
| begin | String | 否 | 筛选的开始时间戳，Unix 时间戳为毫秒数格式 |
| end | String | 否 | 筛选的结束时间戳，Unix 时间戳为毫秒数格式 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### GET / 获取成交明细（近三天）

获取最近3天的成交明细信息，按照成交时间倒序排列。

#### 限速：60次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/fills`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 否 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |
| ordId | String | 否 | 订单ID |
| after | String | 否 | 请求此ID之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此ID之后（更新的数据）的分页内容 |
| begin | String | 否 | 筛选的开始时间戳，Unix 时间戳为毫秒数格式 |
| end | String | 否 | 筛选的结束时间戳，Unix 时间戳为毫秒数格式 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### GET / 获取成交明细（近一年）

获取最近1年的成交明细信息，按照成交时间倒序排列。

#### 限速：10次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/fills-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |
| ordId | String | 否 | 订单ID |
| after | String | 否 | 请求此ID之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此ID之后（更新的数据）的分页内容 |
| begin | String | 否 | 筛选的开始时间戳，Unix 时间戳为毫秒数格式 |
| end | String | 否 | 筛选的结束时间戳，Unix 时间戳为毫秒数格式 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

## 策略交易

### POST / 策略委托下单

策略委托下单

#### 限速：20次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/order-algo`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| tdMode | String | 是 | 交易模式 |
| ccy | String | 否 | 保证金币种 |
| side | String | 是 | 订单方向 |
| ordType | String | 是 | 订单类型 |
| sz | String | 是 | 委托数量 |
| tag | String | 否 | 订单标签 |
| tgtCcy | String | 否 | 委托数量的币种单位 |
| algoClOrdId | String | 否 | 客户自定义策略订单ID |
| closeFraction | String | 否 | 策略委托触发时，平仓的百分比 |
| quickMgnType | String | 否 | 一键借币类型 |
| algoId | String | 否 | 策略订单ID |
| reduceOnly | Boolean | 否 | 是否只减仓 |

### POST / 撤销策略委托订单

撤销策略委托订单

#### 限速：20次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/cancel-algos`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| 请求参数为数组类型，数组中的每个元素都是一个撤销策略委托订单信息的JSON对象 |

### POST / 修改策略委托订单

修改策略委托订单

#### 限速：20次/2s
#### 限速规则：User ID + Instrument ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/trade/amend-algos`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| 请求参数为数组类型，数组中的每个元素都是一个修改策略委托订单信息的JSON对象 |

### GET / 获取策略委托单信息

获取策略委托单信息

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/order-algo`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| algoId | String | 可选 | 策略委托单ID |
| algoClOrdId | String | 可选 | 客户自定义策略订单ID |

### GET / 获取未完成策略委托单列表

获取当前账户下所有未完成的策略委托单信息

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/orders-algo-pending`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ordType | String | 是 | 订单类型 |
| algoId | String | 否 | 策略委托单ID |
| instType | String | 否 | 产品类型 |
| instId | String | 否 | 产品ID |
| after | String | 否 | 请求此ID之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此ID之后（更新的数据）的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### GET / 获取历史策略委托单列表

获取最近3个月的策略委托单信息，按照策略委托单创建时间倒序排列。

#### 限速：20次/2s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/trade/orders-algo-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ordType | String | 是 | 订单类型 |
| state | String | 否 | 订单状态 |
| algoId | String | 否 | 策略委托单ID |
| instType | String | 否 | 产品类型 |
| instId | String | 否 | 产品ID |
| after | String | 否 | 请求此ID之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此ID之后（更新的数据）的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

## 行情数据

### GET / 获取所有产品行情信息

获取所有产品的最新价格快照、买一卖一、24小时交易量等信息。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/tickers`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 `SPOT`：币币 `SWAP`：永续合约 `FUTURES`：交割合约 `OPTION`：期权 |
| uly | String | 否 | 标的指数，仅适用于交割/永续/期权 |
| instFamily | String | 否 | 交易品种，仅适用于交割/永续/期权 |

### GET / 获取单个产品行情信息

获取产品的最新价格快照、买一卖一、24小时交易量等信息。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/ticker`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID，如 BTC-USDT |

### GET / 获取产品深度

获取产品深度列表。

#### 限速：40次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/books`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| sz | String | 否 | 深度档位数量，最大值可传400，即买卖深度共800条 |

### GET / 获取产品完整深度

获取产品完整深度列表。

#### 限速：2次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/books-full`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| sz | String | 否 | 深度档位数量，最大值可传5000，即买卖深度共10000条 |

### GET / 获取交易产品K线数据

获取交易产品的K线数据。K线数据按请求的粒度分组返回，k线数据每个粒度最多可获取最近1,440条。

#### 限速：40次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/candles`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| bar | String | 否 | 时间粒度，默认值1m |
| after | String | 否 | 请求此时间戳之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此时间戳之后（更新的数据）的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为300，不填默认返回100条 |

### GET / 获取交易产品历史K线数据

获取交易产品的历史K线数据。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/history-candles`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| after | String | 否 | 请求此时间戳之前（更旧的数据）的分页内容 |
| before | String | 否 | 请求此时间戳之后（更新的数据）的分页内容 |
| bar | String | 否 | 时间粒度，默认值1m |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### GET / 获取交易产品公共成交数据

获取交易产品的公共成交数据

#### 限速：100次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/trades`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| limit | String | 否 | 分页返回的结果集数量，最大为500，不填默认返回100条 |

### GET / 获取交易产品公共历史成交数据

获取交易产品的公共历史成交数据

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/history-trades`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| type | String | 否 | 分页方向 |
| after | String | 否 | 请求此成交ID之前的分页内容 |
| before | String | 否 | 请求此成交ID之后的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100，不填默认返回100条 |

### GET / 获取平台24小时总成交量

获取平台24小时总成交量。

#### 限速：2次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/platform-24-volume`

### WS / 行情频道

#### 频道名：tickers

获取产品的最新价格快照、买一卖一、24小时交易量等信息。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "tickers",
            "instId": "BTC-USDT"
        }
    ]
}
```

### WS / K线频道

#### 频道名：candle{period}

获取K线数据。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "candle1m",
            "instId": "BTC-USDT"
        }
    ]
}
```

### WS / 交易频道

#### 频道名：trades

获取最新成交数据。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "trades",
            "instId": "BTC-USDT"
        }
    ]
}
```

### WS / 深度频道

#### 频道名：books{depth}

获取深度数据。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "books5",
            "instId": "BTC-USDT"
        }
    ]
}
```

# 公共数据

## REST API

### 获取交易产品基础信息

获取所有可交易产品的信息列表。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/instruments`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |

### 获取预估交割/行权价格

获取预估交割/行权价格。

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/estimated-price`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |

### 获取交割和行权记录

获取交割和行权记录，只有交割和行权之后才有数据。

#### 限速：40次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/delivery-exercise-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取永续合约当前资金费率

获取永续合约当前资金费率

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/funding-rate`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |

### 获取永续合约历史资金费率

获取永续合约历史资金费率

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/funding-rate-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取持仓总量

获取合约整个平台的总持仓量。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/open-interest`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |

### 获取限价

获取合约当前限价信息。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/price-limit`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |

### 获取期权定价

获取期权定价信息

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/opt-summary`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| uly | String | 是 | 标的指数 |
| expTime | String | 否 | 合约到期日 |

### 获取系统时间

获取API服务器的时间。

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/time`

### 获取标记价格

获取合约标记价格。我们设定指数价格加权平均得到标记价格。

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/mark-price`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |

### 获取衍生品仓位档位

获取衍生品仓位档位，每个档位的最大可开仓数量，以及维持保证金率信息。

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/position-tiers`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| tdMode | String | 是 | 保证金模式 |
| uly | String | 否 | 标的指数 |
| instFamily | String | 否 | 交易品种 |
| instId | String | 否 | 产品ID |
| ccy | String | 否 | 保证金币种 |
| tier | String | 否 | 查询指定档位 |

### 获取市场借币杠杆利率和借币限额

获取市场借币杠杆利率和借币限额

#### 限速：5次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/interest-rate-loan-quota`

### 获取衍生品标的指数

获取衍生品标的指数，包括指数价格以及指数成分。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/underlying`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |

### 获取风险准备金余额

获取风险准备金余额信息

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/insurance-fund`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instType | String | 是 | 产品类型 |
| type | String | 否 | 风险准备金类型 |
| uly | String | 否 | 标的指数 |
| ccy | String | 否 | 币种 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 张币转换

该接口为公共接口，不需要身份验证。

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/public/convert-contract-coin`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| type | String | 是 | 转换类型 |
| instId | String | 是 | 产品ID |
| sz | String | 是 | 数量 |
| px | String | 否 | 委托价格 |
| unit | String | 否 | 币的单位 |

### 获取指数行情

获取指数行情数据

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/index-tickers`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| quoteCcy | String | 否 | 指数计价单位 |
| instId | String | 否 | 指数，如 BTC-USD |

### 获取指数K线数据

获取指数的K线数据。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/index-candles`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 指数，如 BTC-USD |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| bar | String | 否 | 时间粒度，默认值1m |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取指数历史K线数据

获取指数历史K线数据。

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/history-index-candles`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 指数，如 BTC-USD |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| bar | String | 否 | 时间粒度，默认值1m |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取标记价格K线数据

获取标记价格的K线数据。

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/mark-price-candles`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| bar | String | 否 | 时间粒度，默认值1m |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取标记价格历史K线数据

获取标记价格历史K线数据。

#### 限速：10次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/history-mark-price-candles`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| instId | String | 是 | 产品ID |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| bar | String | 否 | 时间粒度，默认值1m |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取法币汇率

该接口提供的是2周内的平均汇率数据

#### 限速：1次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/exchange-rate`

### 获取指数成分数据

获取指数成分数据

#### 限速：20次/2s
#### 限速规则：IP
#### HTTP请求

`GET /api/v5/market/index-components`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| index | String | 是 | 指数，如 BTC-USDT |

## WebSocket

### 产品频道

#### 频道名：instruments

获取产品信息数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "instruments",
            "instType": "FUTURES"
        }
    ]
}
```

### 持仓总量频道

#### 频道名：open-interest

获取持仓总量数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "open-interest",
            "instId": "BTC-USDT-SWAP"
        }
    ]
}
```

### 资金费率频道

#### 频道名：funding-rate

获取资金费率数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "funding-rate",
            "instId": "BTC-USDT-SWAP"
        }
    ]
}
```

### 限价频道

#### 频道名：price-limit

获取限价数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "price-limit",
            "instId": "BTC-USDT-SWAP"
        }
    ]
}
```

### 期权定价频道

#### 频道名：opt-summary

获取期权定价数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "opt-summary",
            "uly": "BTC-USD"
        }
    ]
}
```

### 标记价格频道

#### 频道名：mark-price

获取标记价格数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "mark-price",
            "instId": "BTC-USDT-SWAP"
        }
    ]
}
```

### 指数行情频道

#### 频道名：index-tickers

获取指数行情数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "index-tickers",
            "instId": "BTC-USD"
        }
    ]
}
```

### 标记价格K线频道

#### 频道名：mark-price-candle{period}

获取标记价格K线数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "mark-price-candle1m",
            "instId": "BTC-USDT-SWAP"
        }
    ]
}
```

### 指数K线频道

#### 频道名：index-candle{period}

获取指数K线数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "index-candle1m",
            "instId": "BTC-USD"
        }
    ]
}
```

# 资金账户

## REST API

### 获取币种列表

获取平台所有币种列表。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/currencies`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 币种，如 BTC |

### 获取资金账户余额

获取资金账户所有资产列表，查询各币种的余额、冻结和可用等信息。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/balances`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 币种，如 BTC 支持多币种查询（不超过20个），币种之间半角逗号分隔 |

### 获取账户资产估值

查看账户资产估值

#### 限速：1次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/asset-valuation`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 资产估值对应的单位 BTC 、 USDT USD CNY JP EUR KRW VND IDR INR PHP THB TRY AUD SGD ARS |

### 资金划转

在自己账户内部进行资金划转，如交易账户向资金账户划转。

#### 限速：1次/s
#### 限速规则：User ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/asset/transfer`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 是 | 币种，如 USDT |
| amt | String | 是 | 划转数量 |
| from | String | 是 | 转出账户 |
| to | String | 是 | 转入账户 |
| type | String | 否 | 划转类型 |
| subAcct | String | 否 | 子账户名称 |
| clientId | String | 否 | 客户自定义ID |
| omitPosRisk | String | 否 | 是否忽略仓位风险 |

### 获取资金划转状态

获取最近2周的资金划转记录。

#### 限速：1次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/transfer-state`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| transId | String | 可选 | 划转ID |
| clientId | String | 可选 | 客户自定义ID |
| type | String | 否 | 划转类型 |

### 获取资金流水

查询资金账户账单流水数据。流水会有延迟，查询到的数据为上一个小时及之前的数据。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/bills`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 币种 |
| type | String | 否 | 账单类型 |
| after | String | 否 | 请求此时间戳之前的分页内容 |
| before | String | 否 | 请求此时间戳之后的分页内容 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取充值地址信息

获取各个币种的充值地址，包括曾经使用过的老地址。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/deposit-address`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 是 | 币种，如 BTC |

### 获取充值记录

获取所有币种的充值记录，按照时间倒序排列，默认返回100条数据。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/deposit-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 币种，如 BTC |
| depId | String | 否 | 充值记录 ID |
| fromWdId | String | 否 | 内部转账发起方提币申请 ID |
| txId | String | 否 | 区块转账哈希记录 |
| type | String | 否 | 充值方式 |
| state | String | 否 | 状态 |
| after | String | 否 | 查询在此之前的内容，值为时间戳 |
| before | String | 否 | 查询在此之后的内容，值为时间戳 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 提币

用户进行提币操作。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：提现
#### HTTP请求

`POST /api/v5/asset/withdrawal`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 是 | 币种，如 USDT |
| amt | String | 是 | 数量 |
| dest | String | 是 | 提币方式 |
| toAddr | String | 是 | 如果选择链上提币，toAddr必须是认证过的数字货币地址 |
| fee | String | 是 | 网络手续费 |
| chain | String | 可选 | 币种链信息 |
| areaCode | String | 可选 | 手机区号 |
| clientId | String | 否 | 客户自定义ID |

### 撤销提币

撤销提币申请，只有等待中的提币申请可以被撤销。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：提现
#### HTTP请求

`POST /api/v5/asset/cancel-withdrawal`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| wdId | String | 是 | 提币申请ID |

### 获取提币记录

获取所有币种的提币记录，按照申请时间倒序排列，默认返回100条数据。

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/withdrawal-history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| ccy | String | 否 | 币种，如 BTC |
| wdId | String | 否 | 提币申请ID |
| clientId | String | 否 | 客户自定义ID |
| txId | String | 否 | 区块转账哈希记录 |
| type | String | 否 | 提币方式 |
| state | String | 否 | 状态 |
| after | String | 否 | 查询在此之前的内容，值为时间戳 |
| before | String | 否 | 查询在此之后的内容，值为时间戳 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |

### 获取闪兑币种列表

获取闪兑支持的币种列表

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/convert/currencies`

### 获取闪兑币对信息

获取闪兑支持的币对信息

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/convert/currency-pair`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| fromCcy | String | 是 | 消耗币种，如 USDT |
| toCcy | String | 是 | 获得币种，如 BTC |

### 闪兑预估询价

闪兑预估询价

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`POST /api/v5/asset/convert/estimate-quote`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| baseCcy | String | 是 | 交易货币，如 BTC-USDT中的BTC |
| quoteCcy | String | 是 | 计价货币，如 BTC-USDT中的USDT |
| side | String | 是 | 交易方向 |
| rfqSz | String | 是 | 询价数量 |
| rfqSzCcy | String | 是 | 询价币种 |
| clQReqId | String | 否 | 客户自定义询价ID |

### 闪兑交易

闪兑交易

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：交易
#### HTTP请求

`POST /api/v5/asset/convert/trade`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| quoteId | String | 是 | 询价ID |
| baseCcy | String | 是 | 交易货币 |
| quoteCcy | String | 是 | 计价货币 |
| side | String | 是 | 交易方向 |
| sz | String | 是 | 用户交易数量 |
| szCcy | String | 是 | 交易数量币种 |
| clTReqId | String | 否 | 客户自定义交易ID |

### 获取闪兑交易历史

获取闪兑交易历史

#### 限速：6次/s
#### 限速规则：User ID
#### 权限：读取
#### HTTP请求

`GET /api/v5/asset/convert/history`

#### 请求参数

| 参数 | 类型 | 是否必须 | 描述 |
|------|------|----------|------|
| after | String | 否 | 查询在此之前的内容，值为时间戳 |
| before | String | 否 | 查询在此之后的内容，值为时间戳 |
| limit | String | 否 | 分页返回的结果集数量，最大为100 |
| tag | String | 否 | 订单标签 |

## WebSocket

### 充值信息频道

#### 频道名：deposit-info

获取充值信息数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "deposit-info"
        }
    ]
}
```

### 提币信息频道

#### 频道名：withdrawal-info

获取提币信息数据推送。

#### 请求示例

```json
{
    "op": "subscribe",
    "args": [
        {
            "channel": "withdrawal-info"
        }
    ]
}
```

# 错误码

## REST API

### 公共

| 错误码 | HTTP状态码 | 错误提示 |
|--------|------------|----------|
| 0 | 200 | 成功 |
| 1 | 200 | 操作失败 |
| 2 | 200 | 批量操作部分成功 |
| 50000 | 200 | 请求频率过快 |
| 50001 | 200 | 接口请求内容不能为空 |
| 50002 | 200 | 接口请求内容错误 |
| 50004 | 200 | 接口请求超时（不代表请求成功或失败，请检查请求结果） |
| 50005 | 200 | API已下线或无法使用 |
| 50006 | 200 | 无效的Content_Type，请使用"application/json"格式 |
| 50007 | 200 | 账户被冻结 |
| 50008 | 200 | 用户不存在 |
| 50009 | 200 | 账户被暂停 |
| 50010 | 200 | 用户ID不能为空 |
| 50011 | 200 | 用户请求频率过快，超过该接口允许的限额 |
| 50012 | 200 | 账户状态无效 |
| 50013 | 200 | 系统繁忙，请稍后再试 |
| 50014 | 200 | 参数{0}不能为空 |
| 50015 | 200 | 参数{0}或{1}不能为空 |
| 50016 | 200 | 参数{0}不正确 |
| 50017 | 200 | 参数{0}或{1}不正确 |
| 50018 | 200 | 参数{0}或{1}或{2}不正确 |
| 50019 | 200 | 参数{0}或{1}或{2}或{3}不正确 |
| 50020 | 200 | 参数{0}或{1}或{2}或{3}或{4}不正确 |
| 50021 | 200 | 参数{0}或{1}或{2}或{3}或{4}或{5}不正确 |
| 50022 | 200 | 参数{0}不能小于{1} |
| 50023 | 200 | 参数{0}不能大于{1} |
| 50024 | 200 | 参数{0}不能等于{1} |
| 50025 | 200 | 参数{0}应该是{1} |
| 50026 | 200 | 系统错误 |
| 50027 | 200 | 账户受限，请联系客服 |
| 50028 | 200 | 服务器升级，请稍后再试 |
| 50029 | 200 | 账户受限，暂时无法交易 |
| 50030 | 200 | 请求方法错误 |
| 50044 | 200 | {0}无效 |
| 50100 | 200 | API冻结，请联系客服 |
| 50101 | 200 | 经纪商id不存在 |
| 50102 | 200 | 经纪商域名不存在 |
| 50103 | 200 | 经纪商不存在 |
| 50104 | 200 | 经纪商已暂停 |
| 50105 | 200 | 经纪商id不正确 |
| 50106 | 200 | 时间戳请求过期 |
| 50107 | 200 | 请求头"OK-ACCESS-SIGN"不能为空 |
| 50108 | 200 | 请求头"OK-ACCESS-TIMESTAMP"不能为空 |
| 50109 | 200 | 请求头"OK-ACCESS-KEY"不能为空 |
| 50110 | 200 | 请求头"OK-ACCESS-PASSPHRASE"不能为空 |
| 50111 | 200 | 无效的OK-ACCESS-KEY |
| 50112 | 200 | 无效的OK-ACCESS-TIMESTAMP |
| 50113 | 200 | 无效的OK-ACCESS-PASSPHRASE |
| 50114 | 200 | 无效的授权 |
| 50115 | 200 | 无效的请求签名 |
| 50116 | 200 | 时间戳与服务器时间相差过大 |
| 50117 | 200 | 请求过期时间不能早于当前时间 |
| 50118 | 200 | 无效的请求过期时间 |

### 交易类

| 错误码 | HTTP状态码 | 错误提示 |
|--------|------------|----------|
| 51000 | 200 | 参数{0}有误 |
| 51001 | 200 | 产品不存在 |
| 51002 | 200 | 产品未上线 |
| 51003 | 200 | 产品暂停交易 |
| 51004 | 200 | 产品暂停下单 |
| 51005 | 200 | 产品暂停撤单 |
| 51006 | 200 | 产品暂停修改订单 |
| 51007 | 200 | 产品暂停平仓 |
| 51008 | 200 | 产品交易被暂停，当前挂单将被强制撤销 |
| 51009 | 200 | 产品状态异常 |
| 51010 | 200 | 产品类型不匹配 |
| 51011 | 200 | 不支持的下单模式 |
| 51012 | 200 | 下单模式不能为空 |
| 51013 | 200 | 不支持的订单类型 |
| 51014 | 200 | 订单类型不能为空 |
| 51015 | 200 | 不支持的订单方向 |
| 51016 | 200 | 订单方向不能为空 |
| 51017 | 200 | 不支持的交易模式 |
| 51018 | 200 | 交易模式不能为空 |
| 51019 | 200 | 不支持的订单大小 |
| 51020 | 200 | 订单大小不能为空 |
| 51021 | 200 | 不支持的订单价格 |
| 51022 | 200 | 订单价格不能为空 |
| 51023 | 200 | 不支持的业务类型 |
| 51024 | 200 | 业务类型不能为空 |
| 51025 | 200 | 不支持的自成交保护ID |
| 51026 | 200 | 自成交保护ID不能为空 |
| 51027 | 200 | 不支持的自成交保护模式 |
| 51028 | 200 | 自成交保护模式不能为空 |
| 51029 | 200 | 账户模式不能为空 |
| 51030 | 200 | 账户模式{0}不支持{1}交易 |

### 资金类

| 错误码 | HTTP状态码 | 错误提示 |
|--------|------------|----------|
| 58000 | 200 | 账户余额不足 |
| 58001 | 200 | 账户不存在 |
| 58002 | 200 | 账户状态异常 |
| 58003 | 200 | 账户权限不足 |
| 58004 | 200 | 账户被冻结 |
| 58005 | 200 | 用户不存在 |
| 58006 | 200 | 暂停充值 |
| 58007 | 200 | 暂停提币 |
| 58008 | 200 | 提币地址不在白名单 |
| 58009 | 200 | 账户资产被冻结 |
| 58010 | 200 | 转账金额超过日限额 |
| 58011 | 200 | 超过提币限额 |
| 58012 | 200 | 无效的提币地址 |
| 58013 | 200 | 币种暂停服务 |
| 58014 | 200 | 暂停划转 |
| 58015 | 200 | 划转金额超过限额 |
| 58016 | 200 | 划转金额低于最小限额 |
| 58017 | 200 | 账户类型不支持此币种 |
| 58018 | 200 | 提币数量低于最小限额 |
| 58019 | 200 | 提币数量超过最大限额 |
| 58020 | 200 | 提币数量精度有误 |
| 58021 | 200 | 提币地址格式有误 |
| 58022 | 200 | 提币地址和标签不匹配 |
| 58023 | 200 | 提币地址已存在 |
| 58024 | 200 | 提币地址不存在 |
| 58025 | 200 | 提币申请不存在 |
| 58026 | 200 | 提币申请已处理 |
| 58027 | 200 | 无效的网络手续费 |
| 58028 | 200 | 网络手续费过高 |
| 58029 | 200 | 网络手续费过低 |
| 58030 | 200 | 不支持的提币方式 |

### 账户类

| 错误码 | HTTP状态码 | 错误提示 |
|--------|------------|----------|
| 59000 | 200 | 设置失败，请在设置前关闭任何挂单或持仓 |
| 59001 | 200 | 当前存在借币，暂不可切换 |
| 59002 | 200 | 子账户设置失败，请在设置前关闭任何子账户挂单、持仓或策略 |
| 59004 | 200 | 只支持同一业务线下交易产品ID |
| 59005 | 200 | 逐仓自主划转保证金模式，初次划入仓位的资产价值需大于 10,000 USDT |
| 59006 | 200 | 此功能即将下线，无法切换到此模式 |
| 59101 | 200 | 杠杆倍数无法修改，请撤销所有逐仓挂单后进行杠杆倍数修改 |
| 59102 | 200 | 杠杆倍数超过最大杠杆倍数，请降低杠杆倍数 |
| 59103 | 200 | 杠杆倍数过低，账户中没有足够的可用保证金可以追加，请提高杠杆倍数 |
| 59104 | 200 | 杠杆倍数过高，借币仓位已超过该杠杆倍数的最大仓位，请降低杠杆倍数 |
| 59105 | 400 | 杠杆倍数设置不能小于{0}，请提高杠杆倍数 |
| 59106 | 200 | 您下单后仓位总张数所处档位的最高可用杠杆为{0}，请重新调整 |
| 59107 | 200 | 杠杆倍数无法修改，请撤销所有全仓挂单后修改杠杆倍数 |
| 59108 | 200 | 杠杆倍数过低，账户中保证金不足，请提高杠杆倍数 |
| 59109 | 200 | 调整后，账户权益小于所需保证金，请重新调整杠杆倍数 |
| 59200 | 200 | 账户余额不足 |
| 59201 | 200 | 账户余额是负数 |
| 59300 | 200 | 追加保证金失败，指定仓位不存在 |
| 59301 | 200 | 调整保证金超过当前最大可调整数量 |

## WebSocket

### 公共

| 错误码 | 错误消息 |
|--------|----------|
| 60004 | 无效的 timestamp |
| 60005 | 无效的 apiKey |
| 60006 | 请求时间戳过期 |
| 60007 | 无效的签名 |
| 60008 | 当前服务不支持订阅{0}频道，请检查WebSocket地址 |
| 60009 | 登录失败 |
| 60011 | 用户需要登录 |
| 60012 | 不合法的请求 |
| 60013 | 无效的参数 args |
| 60014 | 用户请求频率过快，超过该接口允许的限额 |
| 60018 | 错误的 URL 或者 {0} 不存在，请参考 API 文档使用正确的 URL，频道和参数 |
| 60019 | 无效的op{0} |
| 60023 | 批量登录请求过于频繁 |
| 60024 | passphrase不正确 |
| 60026 | 不支持APIKey和token同时登录 |
| 60027 | 参数{0}不可为空 |
| 60028 | 当前服务不支持此功能，请检查WebSocket地址 |

---

**注意：** 此文档包含了OKX API的主要接口和功能说明。完整的API文档内容非常庞大，这里提供了核心的接口信息。如需了解更多详细信息，请访问官方API文档网站。

**免责声明：** 本文档仅供参考，具体的API接口参数和返回值请以官方最新文档为准。在使用API进行交易时，请务必谨慎操作，注意风险控制。
