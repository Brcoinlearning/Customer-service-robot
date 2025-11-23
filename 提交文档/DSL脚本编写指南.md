# DSL脚本编写指南

## 1. DSL文法定义

### 1.1 总体结构文法

```
<DSL脚本> ::= "flow:" <流程配置>

<流程配置> ::= 
    "name:" <字符串>
    "version:" <字符串>?
    "description:" <字符串>?
    "business_line:" <字符串>
    "process_order:" <槽位顺序列表>
    "slots:" <槽位定义字典>
    "events:" <事件处理字典>?
    "commands:" <命令映射字典>?
    "validations:" <验证规则列表>?
    "templates:" <自定义模板字典>?
```

### 1.2 槽位定义文法

```
<槽位定义字典> ::= 
    <槽位名称> ":" <槽位配置>

<槽位配置> ::=
    "label:" <字符串>
    "description:" <字符串>
    "required:" <布尔值>
    ("type:" ("enum" | "text"))?
    ("enums_key:" <字符串>)?
    ("dependencies:" <依赖列表>)?
    ("semantic_stage:" <字符串>)?
    ("allow_llm:" <布尔值>)?
    ("prompt_template:" <字符串>)?
    ("help:" <字符串>)?
    ("validation:" <验证配置>)?

<依赖列表> ::= "[" <槽位名称列表> "]"
<槽位名称列表> ::= <槽位名称> ("," <槽位名称>)*
```

### 1.3 事件处理文法

```
<事件处理字典> ::=
    <事件名称> ":" <动作列表>

<事件名称> ::= 
    "on_start" | "on_all_filled" | "on_confirm" | "on_restart"

<动作列表> ::= "[" <动作定义> ("," <动作定义>)* "]"

<动作定义> ::=
    "-" "action:" <动作名称>
    ("template:" <字符串>)?
    ("description:" <字符串>)?

<动作名称> ::=
    "reset_form" | "auto_fill_single_options" | "show_template" |
    "show_summary" | "submit_order" | "validate_form" | "ask_continue"
```

### 1.4 命令映射文法

```
<命令映射字典> ::=
    <命令名称> ":" <命令配置>

<命令配置> ::=
    "keywords:" <关键词列表>
    "action:" <动作名称>
    ("description:" <字符串>)?
    ("condition:" <条件表达式>)?
    ("available_when:" <可用条件>)?
    ("response:" <多行字符串>)?

<关键词列表> ::= "[" <字符串列表> "]"
<可用条件> ::= "always" | "any_slot_filled" | "all_slots_filled"
```

## 2. 核心语法元素说明

### 2.1 数据类型定义

#### 2.1.1 基本数据类型

- **字符串**：双引号包裹的文本，支持Unicode字符
- **布尔值**：`true` 或 `false`
- **数字**：整数或浮点数
- **列表**：方括号包裹的元素序列，元素间用逗号分隔
- **字典**：键值对集合，键为字符串，值可为任意类型

#### 2.1.2 特殊值类型

- **槽位名称**：由字母、数字、下划线组成，需在process_order中定义
- **业务线标识**：对应业务配置目录中的JSON文件名
- **枚举键名**：对应业务配置中enums字典的键
- **模板键名**：对应业务配置中templates字典的键

### 2.2 流程控制元素

#### 2.2.1 依赖关系定义

```yaml
dependencies: [brand, category]  # 依赖多个前置槽位
dependencies: []                 # 无依赖，可首先填充
```

**语义**：定义槽位填充的顺序约束，确保前置条件满足后才提示当前槽位。

#### 2.2.2 条件执行

```yaml
condition: all_slots_filled      # 所有槽位填充时可用
available_when: any_slot_filled  # 任意槽位填充时可用
```

**语义**：控制命令和动作的可用性条件，实现上下文感知的交互逻辑。

### 2.3 语义处理元素

#### 2.3.1 语义阶段标识

```yaml
semantic_stage: chip_selection    # 芯片选择语义阶段
semantic_stage: storage_select    # 存储选择语义阶段
```

**语义**：标识槽位的语义处理阶段，用于动态选项构建和智能推荐。

#### 2.3.2 AI使用控制

```yaml
allow_llm: true    # 允许LLM填充该槽位
allow_llm: false   # 禁止LLM填充，仅使用本地匹配
```

**语义**：控制是否使用AI进行槽位填充，平衡智能性与可控性。

## 3. 完整用法说明

### 3.1 脚本文件结构

#### 3.1.1 必需部分

每个DSL脚本必须包含以下核心部分：

```yaml
flow:
  name: "业务流程名称"           # 必需：流程标识
  business_line: "业务线名称"     # 必需：关联的业务配置
  process_order:                 # 必需：槽位执行顺序
    - 槽位1
    - 槽位2
  slots:                         # 必需：槽位定义
    槽位1:
      label: "显示标签"
      description: "业务描述"
      required: true
```

#### 3.1.2 可选扩展部分

根据业务复杂度可选包含：

```yaml
events:                         # 可选：事件处理
  on_start:
    - action: show_template
      template: form_welcome
    
commands:                       # 可选：用户命令
  help:
    keywords: ["帮助", "help"]
    action: show_help
  
validations:                    # 可选：验证规则
  - name: "业务规则验证"
    rules: [...]
  
templates:                      # 可选：自定义模板
  custom_welcome:
    - "自定义欢迎信息"
```

### 3.2 槽位定义详解

#### 3.2.1 基础槽位定义

```yaml
category:
  label: "产品大类"
  description: "选择产品类型"
  required: true
  type: enum
  enums_key: category
  dependencies: []
  prompt_template: form_category_prompt
```

**字段说明**：

- `label`：用户可见的显示名称
- `description`：业务描述，用于文档和提示
- `required`：是否必须填充
- `type`：数据类型，enum或text
- `enums_key`：枚举配置键，对应业务JSON中的enums
- `dependencies`：依赖的前置槽位
- `prompt_template`：使用的提示模板

#### 3.2.2 高级槽位特性

```yaml
chip:
  label: "处理器芯片"
  description: "选择处理器型号"
  required: true
  allow_llm: true
  type: enum
  enums_key: chip
  dependencies: [category, series, size]
  semantic_stage: chip_selection
  validation:
    must_be_valid_enum: true
    min_confidence: 0.35
  help: "根据使用场景选择合适的芯片型号"
```

**高级特性**：

- `allow_llm`：启用AI智能填充
- `semantic_stage`：启用语义映射
- `validation`：值验证规则
- `help`：用户帮助信息

### 3.3 事件处理机制

#### 3.3.1 生命周期事件

```yaml
events:
  on_start:                    # 流程开始时触发
    - action: reset_form
    - action: show_template
      template: form_welcome
    
  on_all_filled:               # 所有必填槽位填充时触发
    - action: show_summary
    - action: ask_confirm
  
  on_confirm:                  # 用户确认时触发
    - action: validate_form
    - action: submit_order
    - action: show_template
      template: form_order_confirmed
    
  on_restart:                  # 重新开始时触发
    - action: reset_form
    - action: show_welcome
```

**事件说明**：

- `on_start`：初始化流程，显示欢迎信息
- `on_all_filled`：表单完成时显示摘要和确认选项
- `on_confirm`：订单确认时执行验证和提交
- `on_restart`：重置流程状态，重新开始

#### 3.3.2 动作类型

```yaml
- action: reset_form                    # 重置表单状态
- action: auto_fill_single_options      # 自动填充单选项
- action: show_template                 # 显示模板内容
- action: show_summary                  # 显示订单摘要
- action: submit_order                  # 提交订单
- action: validate_form                 # 验证表单数据
- action: ask_continue                  # 询问是否继续
```

### 3.4 命令映射配置

#### 3.4.1 基础命令定义

```yaml
commands:
  restart:                        # 命令标识
    keywords:                     # 触发关键词
      - "重新开始"
      - "重置"
      - "reset"
    action: restart_flow          # 执行动作
    description: "清空所有选择重新开始"
  
  confirm:
    keywords: ["确认", "好的", "ok", "yes"]
    action: confirm_order
    condition: all_slots_filled   # 执行条件
    description: "确认当前订单"
```

#### 3.4.2 高级命令特性

```yaml
help:
  keywords: ["帮助", "help", "?"]
  action: show_help
  available_when: always          # 可用条件
  response: |                     # 直接响应内容
    使用帮助：
  
    • 按照提示选择产品配置
    • 可以直接说名称或输入数字
    • 说"重选"修改之前的选择
    • 说"帮助"查看本说明
  
  description: "显示使用帮助信息"
```

## 4. 完整范例

### 4.1 苹果专卖店购物流程

```yaml
# apple_store.flow.yaml
flow:
  name: apple_shopping
  version: "1.0"
  description: "苹果产品智能购物流程"
  business_line: apple_store
  
  process_order:
    - category
    - brand
    - series
    - size
    - chip
    - storage
    - color

  slots:
    category:
      label: "产品大类"
      description: "选择产品类型"
      required: true
      allow_llm: false
      type: enum
      enums_key: category
      dependencies: []
      prompt_template: form_category_prompt
      help: "我们有Mac电脑、iPhone手机和iPad平板三大类产品"
    
    brand:
      label: "品牌选择"
      description: "品牌选择"
      required: true
      allow_llm: false
      type: enum
      enums_key: brand
      dependencies: [category]
      prompt_template: form_brand_prompt
      auto_fill: true
    
    series:
      label: "产品系列"
      description: "选择具体产品系列"
      required: true
      allow_llm: false
      type: enum
      enums_key: series
      semantic_stage: series_selection
      dependencies: [brand]
      prompt_template: form_series_prompt
      conditional_prompts:
        - condition: "category == '电脑'"
          template: form_series_prompt_computer
        - condition: "category == '手机'"
          template: form_series_prompt_phone
      help: "根据您选择的类别，为您推荐合适的系列"
    
    chip:
      label: "处理器芯片"
      description: "选择处理器型号"
      required: true
      allow_llm: true
      type: enum
      enums_key: chip
      semantic_stage: chip_selection
      dependencies: [category, series, size]
      prompt_template: form_chip_prompt
      validation:
        must_be_valid_enum: true
        min_confidence: 0.35

  events:
    on_start:
      - action: reset_form
        description: "重置表单状态"
      - action: auto_fill_single_options
        description: "自动填充单选项"
      - action: show_template
        template: form_welcome
        description: "显示欢迎信息"
  
    on_all_filled:
      - action: show_summary
        description: "显示订单摘要"
      - action: show_template
        template: form_confirmation_options
        description: "显示确认选项"

  commands:
    restart:
      keywords: ["重新开始", "重置", "reset"]
      action: restart_flow
      available_when: always
    
    confirm:
      keywords: ["确认", "下单", "ok", "yes"]
      action: confirm_order
      condition: all_slots_filled
    
    help:
      keywords: ["帮助", "help", "?"]
      action: show_help
      response: |
        📖 使用帮助：
      
        • 按照提示选择产品配置
        • 可以直接说名称，也可以输入数字
        • 随时说"重选"可以修改之前的选择
        • 说"重新开始"可以清空重来
        • 说"查看"可以看当前订单
        • 说"帮助"查看本说明
```

### 4.2 餐饮预订流程

```yaml
# dining.flow.yaml
flow:
  name: dining_reservation
  version: "1.0"
  description: "餐厅预订智能表单流程"
  business_line: dining
  
  process_order:
    - category
    - brand
    - series
    - party_size
    - date
    - contact

  slots:
    category:
      label: "预订类型"
      description: "预订类型"
      required: true
      allow_llm: false
      type: enum
      enums_key: dining_category
      dependencies: []
      prompt_template: form_category_prompt
      auto_fill: true
    
    brand:
      label: "餐厅选择"
      description: "选择餐厅"
      required: true
      allow_llm: false
      type: enum
      enums_key: dining_brand
      dependencies: [category]
      prompt_template: form_brand_prompt
      semantic_stage: brand
    
    series:
      label: "用餐时段"
      description: "选择用餐时段"
      required: true
      allow_llm: false
      type: enum
      enums_key: dining_series
      dependencies: [brand]
      prompt_template: form_series_prompt
      semantic_stage: series

    party_size:
      label: "用餐人数"
      description: "用餐人数"
      required: true
      allow_llm: false
      type: enum
      enums_key: party_size
      dependencies: [series]
      prompt_template: form_party_size_prompt
      semantic_stage: party_size

    date:
      label: "预订日期"
      description: "预订日期"
      required: true
      allow_llm: true
      type: enum
      enums_key: date
      dependencies: [party_size]
      prompt_template: form_date_prompt
      validation:
        must_be_valid_enum: true
        min_confidence: 0.35
      
    contact:
      label: "联系方式"
      description: "联系方式"
      required: true
      allow_llm: true
      type: text
      dependencies: [date]
      prompt_template: form_contact_prompt

  events:
    on_start:
      - action: reset_form
      - action: show_template
        template: form_welcome
  
    on_all_filled:
      - action: show_summary
      - action: ask_confirm
    
    on_confirm:
      - action: validate_form
      - action: submit_order
      - action: show_template
        template: form_order_confirmed
      - action: show_template
        template: form_order_thanks
      - action: ask_continue

  commands:
    restart:
      keywords: ["重新预订", "重来", "reset"]
      action: restart_flow
    
    confirm:
      keywords: ["确认", "好的", "是的", "没问题"]
      condition: all_slots_filled
      action: confirm_order
    
    modify:
      keywords: ["修改", "改一下", "重选"]
      action: enter_reselect_mode
    
    help:
      keywords: ["帮助", "help"]
      action: show_help
      response: |
        📖 预订帮助：
      
        • 按照提示提供预订信息
        • 可以说"修改"重新选择某项
        • 说"重新预订"可以清空重来
        • 说"帮助"查看本说明
```

### 4.3 简单问答流程范例

```yaml
# simple_qa.flow.yaml
flow:
  name: simple_qa
  version: "1.0"
  description: "简单问答收集流程"
  business_line: apple_store  # 复用现有业务配置
  
  process_order:
    - user_name
    - question_type
    - question_detail
    - contact_info

  slots:
    user_name:
      label: "您的姓名"
      description: "用户姓名"
      required: true
      allow_llm: true
      type: text
      dependencies: []
      prompt_template: form_name_prompt
    
    question_type:
      label: "问题类型"
      description: "选择问题类型"
      required: true
      allow_llm: true
      type: enum
      enums_key: question_type
      dependencies: [user_name]
      prompt_template: form_question_type_prompt
    
    question_detail:
      label: "问题描述"
      description: "详细问题描述"
      required: true
      allow_llm: true
      type: text
      dependencies: [question_type]
      prompt_template: form_question_detail_prompt
    
    contact_info:
      label: "联系方式"
      description: "回复联系方式"
      required: false
      allow_llm: true
      type: text
      dependencies: [question_detail]
      prompt_template: form_contact_prompt

  events:
    on_start:
      - action: show_template
        template: qa_welcome
      
    on_all_filled:
      - action: show_summary
      - action: show_template
        template: qa_thanks

  commands:
    skip:
      keywords: ["跳过", "不想填", "skip"]
      action: skip_current_slot
    
    back:
      keywords: ["上一步", "返回", "back"]
      action: go_previous_slot
```

## 5. 实践指南

### 5.1 槽位设计原则

#### 5.1.1 合理的依赖关系

```yaml
# 推荐：清晰的依赖链
slots:
  category:
    dependencies: []           # 无依赖，首先填充
  
  brand:
    dependencies: [category]   # 依赖类别
  
  series:
    dependencies: [brand]      # 依赖品牌
  
  size:
    dependencies: [series]     # 依赖系列
```

**原则**：建立清晰的依赖链条，避免循环依赖。确保用户按逻辑顺序提供信息。

#### 5.1.2 智能填充策略

```yaml
# 混合使用不同填充策略
slots:
  category:
    allow_llm: false           # 关键选择，禁用AI
  
  color:
    allow_llm: true            # 主观选择，启用AI
  
  contact:
    allow_llm: true            # 自由文本，启用AI
```

**原则**：关键业务选择使用精确匹配，主观和自由文本使用AI增强。

### 5.2 事件处理设计

#### 5.2.1 渐进式反馈

```yaml
events:
  on_start:
    - action: show_template    # 欢迎信息
      template: form_welcome
    
  on_all_filled:
    - action: show_summary     # 完成反馈
    - action: ask_confirm      # 确认提示
  
  on_confirm:
    - action: show_template    # 成功反馈
      template: form_success
```

**原则**：在每个关键节点提供适当的用户反馈，增强交互体验。

### 5.3 命令设计建议

#### 5.3.1 覆盖主要用户意图

```yaml
commands:
  # 流程控制
  restart: [...]               # 重新开始
  confirm: [...]               # 确认操作
  
  # 导航控制  
  back: [...]                  # 返回上一步
  skip: [...]                  # 跳过当前
  
  # 信息查询
  help: [...]                  # 帮助信息
  status: [...]                # 当前状态
```

**原则**：覆盖用户可能的主要操作意图，提供流畅的流程控制。
