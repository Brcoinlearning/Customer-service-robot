# Customer-service-robot

客服机器人的程序设计实践


# 当前项目结构参考手册

## 项目根目录结构

```
Customer-service-robot/
├── 开发日志.md                    # 记录开发过程和Git提交历史
├── 任务计划.md                    # 项目阶段划分和时间安排
├── 需求分析.md                    # 功能需求和非功能需求文档
├── 要求.md                       # 项目原始要求文件
├── DSL设计.md                    # DSL语法设计和范例说明
├── README.md                     # 项目简介和使用说明
├── requirements.txt              # Python项目依赖包列表
└── 2025程序设计实践-大作业项目文档v3.docx  # 完整项目文档
```

## 源代码目录结构 (src/)

```
src/
├── main.py                      # 程序主入口文件
├── config/                      # 配置管理模块
│   └── settings.py              # 集中管理所有配置项
├── core/                        # 核心架构模块
│   ├── interfaces.py            # 定义各模块的接口规范
│   └── context.py               # 对话上下文状态管理
├── parser/                      # DSL解析器模块
│   └── dsl_parser.py            # DSL脚本解析核心逻辑
├── interpreter/                 # 解释执行器模块
│   └── interpreter.py           # 规则匹配和动作执行
├── llm/                         # LLM集成模块
│   └── spark_client.py          # 星火API调用客户端
├── scripts/                     # DSL脚本目录
│   └── ecommerce.dsl            # 电商客服业务脚本
└── __pycache__/                 # Python字节码缓存（可忽略）
```

## 测试目录结构 (tests/)

```
tests/
├── test_parser.py               # DSL解析器单元测试
└── test_spark_api.py            # LLM API调用测试
```

## 各核心文件功能说明

### 程序入口

- **main.py** - 程序启动入口，负责初始化各模块和主循环

### 配置管理

- **config/settings.py** - 集中管理配置：
  - API密钥和URL
  - 文件路径配置
  - 超时和限制参数

### 核心架构

- **core/interfaces.py** - 定义接口规范：
  - IDSLParser: DSL解析器接口
  - IInterpreter: 解释执行器接口
  - ILLMClient: LLM客户端接口
  - IContextManager: 上下文管理器接口
- **core/context.py** - 管理对话状态：
  - 记录对话历史
  - 存储用户变量
  - 跟踪当前意图

### 业务模块

- **parser/dsl_parser.py** - DSL脚本解析：
  - 解析INTENT定义
  - 解析RULE规则
  - 语法验证和错误处理
- **interpreter/interpreter.py** - 规则执行：
  - 意图匹配
  - 动作序列执行
  - 默认规则处理
- **llm/spark_client.py** - AI集成：
  - 星火API调用
  - 意图识别
  - 错误处理和降级

### 业务脚本

- **scripts/ecommerce.dsl** - 业务逻辑定义：
  - 意图类型定义
  - 业务规则编写
  - 响应内容配置

## 调试参考指南

### 修改API配置

编辑：`src/config/settings.py`

```python
LLM_API_KEY = "你的新API密钥"
```

### 修改业务逻辑

编辑：`src/scripts/ecommerce.dsl`

```dsl
RULE your_rule
WHEN INTENT_IS your_intent
THEN
    RESPOND "你的响应内容"
```

### 添加新的意图类型

1. 在 `ecommerce.dsl` 中添加INTENT定义
2. 在 `interpreter.py` 中添加对应的规则处理

### 调试解析问题

查看：`src/parser/dsl_parser.py` 的解析日志

### 调试执行问题

查看：`src/interpreter/interpreter.py` 的规则匹配过程

### 调试API调用

查看：`src/llm/spark_client.py` 的请求和响应处理

这个结构为后续开发和调试提供了清晰的模块划分和职责分离。
