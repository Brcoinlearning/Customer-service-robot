# 客服机器人 - 表单版本 (Form-Based System)

## 📌 项目说明

这是**表单版本**的客服机器人系统，采用多槽位信息采集的对话方式。

完整的 **DSL 版本** 已备份在：`../大作业-DSL版本/`

## 🏗️ 架构特点

- **表单式对话流程**：逐步收集用户需求（品类 → 品牌 → 系列 → 配置）
- **统一业务配置**：所有业务逻辑配置化（`business_configs/`）
- **多层信息抽取**：
  1. 直接关键词匹配（最快）
  2. 语义映射（本地）
  3. LLM 补全（兜底）
- **通用化设计**：支持多业务场景（苹果专卖店、餐饮预订等）

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行表单版本
python src/main.py
```

## 📁 目录结构

```
src/
├── main.py                    # 表单版本入口（原 main_with_form.py）
├── core/
│   ├── form_based_system.py  # 表单对话系统核心
│   ├── form_adapter.py        # 适配器（可选）
│   ├── interfaces.py          # 接口定义
│   └── context.py             # 上下文管理
├── knowledge/
│   ├── business_config_loader.py  # 统一配置加载器
│   ├── business_configs/          # 业务配置文件
│   │   ├── apple_store.json       # 苹果专卖店配置
│   │   └── dining.json            # 餐饮预订配置
│   ├── product_knowledge.py       # 产品知识库
│   └── data/                      # 数据文件
├── llm/
│   └── spark_client.py        # 星火 LLM 客户端
├── semantics/
│   └── option_mapping.py      # 语义映射
└── config/
    └── settings.py            # 配置管理
```

## 🔄 版本差异

| 特性 | DSL 版本 | 表单版本 |
|------|---------|---------|
| 对话流程 | DSL 脚本驱动 | 表单槽位驱动 |
| 配置方式 | `.dsl` 脚本 | `.json` 配置 |
| 扩展性 | 需要编写 DSL | 修改 JSON 即可 |
| 业务逻辑 | 规则引擎 | 状态机 + 槽位 |
| 适用场景 | 复杂规则 | 结构化信息采集 |

## 📊 支持的业务场景

1. **苹果专卖店** (`apple_store`)
   - 产品类别：电脑、手机、平板
   - 配置选项：系列、尺寸、芯片、存储、颜色
   
2. **餐饮预订** (`dining`)
   - 餐厅选择：海底捞、西贝莜面村、外婆家
   - 预订信息：用餐时段、人数、日期、联系方式

## 🎯 核心特性

### 1. 数字选择优先（不走 LLM）
所有纯数字输入直接映射到选项，完全不调用 LLM：
```
用户: 1
系统: ✅ 产品大类: 电脑 (数字)
```

### 2. 通用命令关键词
从配置文件加载命令关键词：
```json
"command_keywords": {
  "confirm": ["确认", "确认订单", "下单", ...],
  "reselect": ["重选", "修改", ...],
  "restart": ["重新开始", ...]
}
```

### 3. 动态别名匹配
所有产品/选项支持多个别名：
```json
{"label": "MacBook Air", "aliases": ["air", "macbook air", "轻薄"]}
```

### 4. 动态过滤规则
根据已选项动态筛选后续选项：
```json
"size_by_series": {
  "MacBook Air": ["13寸", "15寸"],
  "MacBook Pro": ["14寸", "16寸"]
}
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_parser.py
pytest tests/test_memory_features.py
```

## 📝 开发日志

详细的开发历程见：[开发日志.md](开发日志.md)

最新更新（2025-11-19）：
- ✅ 完成硬编码到配置化的迁移
- ✅ 实现通用数字选择逻辑
- ✅ 完善餐饮预订场景配置

## 🔗 相关文档

- [统一业务配置架构总结.md](统一业务配置架构总结.md)
- [后续优化方向.md](后续优化方向.md)
- [现存bug.md](现存bug.md)

---

💡 **提示**：如需查看或运行 DSL 版本，请切换到 `../大作业-DSL版本/` 目录
