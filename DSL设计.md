# DSL脚本语言设计

### 1. DSL设计原则

- **简洁性**：语法简单易懂，便于业务人员理解
- **表达力**：能够描述复杂的客服对话逻辑
- **可扩展性**：易于添加新的意图类型和响应动作
- **集成友好**：便于与LLM API集成进行意图识别

### 2. DSL语法定义（BNF格式）

```
<program> ::= <statement>+

<statement> ::= <rule_definition> | <intent_definition>

<intent_definition> ::= "INTENT" <identifier> ":" <string_literal>

<rule_definition> ::= "RULE" <identifier> 
                      "WHEN" <condition> 
                      "THEN" <action>+

<condition> ::= <intent_condition> | <keyword_condition> | <compound_condition>

<intent_condition> ::= "INTENT_IS" <identifier>

<keyword_condition> ::= "CONTAINS_KEYWORD" "[" <string_literal> ("," <string_literal>)* "]"

<compound_condition> ::= <condition> ("AND" | "OR") <condition>

<action> ::= <response_action> | <transfer_action> | <end_action> | <set_variable_action>

<response_action> ::= "RESPOND" <string_literal>

<transfer_action> ::= "TRANSFER_TO" <identifier>

<end_action> ::= "END_CONVERSATION"

<set_variable_action> ::= "SET" <identifier> "=" <expression>

<expression> ::= <string_literal> | <number> | <boolean>

<identifier> ::= [a-zA-Z_][a-zA-Z0-9_]*

<string_literal> ::= "\"" [^"]* "\""

<number> ::= [0-9]+

<boolean> ::= "TRUE" | "FALSE"
```

### 3. DSL语义说明

#### 核心概念：

- **INTENT**：定义意图类型，与LLM识别的意图对应
- **RULE**：业务规则，包含条件和相应的动作
- **WHEN**：触发条件（意图匹配或关键词匹配）
- **THEN**：满足条件后执行的动作序列

#### 执行流程：

1. 用户输入传递给LLM进行意图识别
2. 解释器按顺序匹配规则条件
3. 执行第一个匹配规则的THEN部分
4. 如果没有规则匹配，执行默认规则

### 4. 脚本范例

#### 范例1：电商客服场景

```dsl
# 电商客服DSL脚本
INTENT greeting: "问候和欢迎"
INTENT product_query: "产品咨询"
INTENT order_status: "订单状态查询"
INTENT return_request: "退货申请"
INTENT complaint: "投诉建议"

# 默认规则
RULE default_rule
WHEN TRUE
THEN
    RESPOND "抱歉，我没有理解您的问题。请您重新描述，或联系人工客服。"
    END_CONVERSATION

# 问候处理
RULE greeting_rule
WHEN INTENT_IS greeting
THEN
    RESPOND "您好！欢迎来到XX电商客服中心，请问有什么可以帮您？"

# 产品咨询
RULE product_query_rule
WHEN INTENT_IS product_query
THEN
    RESPOND "感谢您对我们产品的关注！请告诉我您想了解哪类产品？"
    RESPOND "我们有电子产品、家居用品、服装配饰等多个品类可供选择。"

# 订单查询
RULE order_status_rule
WHEN INTENT_IS order_status OR CONTAINS_KEYWORD ["订单", "物流", "发货"]
THEN
    RESPOND "我来帮您查询订单状态。"
    RESPOND "请提供您的订单号，或者您也可以在我们的APP中查看最新物流信息。"

# 退货申请
RULE return_rule
WHEN INTENT_IS return_request
THEN
    RESPOND "理解您想要退货的需求。"
    RESPOND "我们的退货政策是：7天内无理由退货，商品需保持完好。"
    RESPOND "请告诉我您的订单号和退货原因，我将为您处理。"
```

#### 范例2：技术支持场景

```dsl
# 技术支持DSL脚本
INTENT login_issue: "登录问题"
INTENT feature_question: "功能咨询"
INTENT bug_report: "问题反馈"
INTENT account_help: "账户帮助"

# 登录问题
RULE login_help
WHEN INTENT_IS login_issue OR CONTAINS_KEYWORD ["登录", "密码", "无法登录"]
THEN
    RESPOND "抱歉听到您遇到登录问题。"
    RESPOND "建议您：1. 检查网络连接 2. 重置密码 3. 清除浏览器缓存"
    RESPOND "如果问题仍然存在，请提供错误截图，我们将进一步协助。"

# 功能咨询
RULE feature_help
WHEN INTENT_IS feature_question
THEN
    RESPOND "很高兴为您介绍产品功能！"
    RESPOND "我们最近更新了文件共享和团队协作功能。"
    RESPOND "您具体想了解哪个功能呢？"

# 问题反馈
RULE bug_handling
WHEN INTENT_IS bug_report OR CONTAINS_KEYWORD ["bug", "错误", "崩溃"]
THEN
    RESPOND "感谢您反馈问题！"
    RESPOND "为了更好地解决，请告诉我们："
    RESPOND "1. 问题的具体表现 2. 出现时间 3. 使用的设备和系统版本"
    SET priority = "high"
```

#### 范例3：银行客服场景

```dsl
# 银行客服DSL脚本
INTENT balance_query: "余额查询"
INTENT transfer_help: "转账咨询"
INTENT card_issue: "卡片问题"
INTENT loan_info: "贷款信息"

# 余额查询
RULE balance_rule
WHEN INTENT_IS balance_query OR CONTAINS_KEYWORD ["余额", "多少钱", "剩余"]
THEN
    RESPOND "为了保护您的账户安全，余额查询需要通过手机银行或网上银行进行。"
    RESPOND "您可以通过我们的官方APP实时查看账户余额和交易明细。"

# 转账咨询
RULE transfer_rule
WHEN INTENT_IS transfer_help
THEN
    RESPOND "我行支持以下转账方式："
    RESPOND "1. 行内转账：实时到账，免手续费"
    RESPOND "2. 跨行转账：1-2个工作日，手续费根据金额计算"
    RESPOND "3. 国际汇款：需要提供收款人详细信息"

# 卡片问题
RULE card_help
WHEN INTENT_IS card_issue OR CONTAINS_KEYWORD ["卡", "丢失", "盗刷"]
THEN
    RESPOND "如果您的卡片丢失或发现异常交易，请立即："
    RESPOND "1. 拨打24小时客服热线400-XXX-XXXX进行挂失"
    RESPOND "2. 通过手机银行临时冻结卡片"
    RESPOND "3. 前往最近网点办理补卡手续"
    SET urgent = TRUE
```

### 5. 设计说明

#### 关键特性：

1. **意图驱动**：基于LLM识别的意图执行相应规则
2. **条件组合**：支持AND/OR逻辑组合，增强匹配灵活性
3. **动作序列**：支持多个响应动作，实现多轮对话
4. **变量支持**：可设置上下文变量，用于状态跟踪
5. **易于扩展**：新增意图类型和动作类型简单

#### 与LLM集成：

- LLM API负责将用户自然语言映射到预定义的INTENT
- 解释器根据匹配的INTENT执行相应的RULE
- 支持回退机制（默认规则）处理未知意图
