---
name: your-skill-name
description: TODO - 替换为清晰的描述，包括：1) 这个技能做什么 2) 什么时候应该触发 3) 具体使用场景。这是 AI 判断是否调用这个技能的主要依据。
---

# Your Skill Name

> **⚠️ AI 填充指南（生成后删除此部分）**
>
> 生成此模板后，AI 必须根据用户需求自动填充以下内容，不要留占位符：
>
> 1. **description**：必须包含三要素：
>    - 做什么（功能）
>    - 什么时候用（触发场景）
>    - 具体例子（用户会怎么说）
>
> 2. **Overview**：用 2-3 句话说清楚：
>    - 这个技能解决什么问题？
>    - 用户为什么需要它？
>
> 3. **Workflow**：必须是可执行的具体步骤，不要写"第一步、第二步"
>    - 每一步都要有明确的动作
>    - 如果需要运行脚本，写出具体命令
>    - 如果需要调用 API，写出具体端点
>
> 4. **Key Rules**：写真正的规则，不要写"规则一、规则二"
>    - 边界情况怎么处理？
>    - 错误怎么处理？
>    - 有什么注意事项？
>
> 5. **Gotchas**：必须添加这个部分
>    - 最容易出错的地方是什么？
>    - 有什么坑要避免？
>
> **示例（天气查询技能）：**
> ```
> ---
> name: weather-skill
> description: 查询指定城市的实时天气。当用户问"今天天气怎么样"、"北京气温多少"、"穿什么衣服"时使用。
> ---
>
> # 天气查询技能
>
> ## Overview
> 查询指定城市的实时天气，包括温度、天气状况、湿度、风力。
> 解决用户"今天穿什么"、"要不要带伞"等问题。
>
> ## Workflow
> 1. 从用户问题中提取城市名称
> 2. 运行 `python3 scripts/weather.py --city "城市名"`
> 3. 格式化输出："北京当前温度 25°C，多云，湿度 60%"
>
> ## Key Rules
> - 城市名必须是中文
> - 不支持查询未来天气
> - 最多查询 5 个城市/次
>
> ## Gotchas
> - 城市名不匹配时返回随机数据，要提示用户
> - 网络超时要重试 1 次
> ```

## Overview
TODO - 用 2-3 句话说清楚这个技能解决什么问题

## Workflow
TODO - 写出具体可执行的步骤，不要写"第一步、第二步"

1. TODO - 具体动作
2. TODO - 具体动作
3. TODO - 具体动作

## Key Rules
TODO - 写真正的规则，不要写"规则一、规则二"

- TODO - 边界情况怎么处理？
- TODO - 错误怎么处理？
- TODO - 有什么注意事项？

## Gotchas
TODO - 最容易出错的地方，有什么坑要避免

- TODO - 坑 1
- TODO - 坑 2

## Bundled Resources
- Detailed documentation: see `references/` directory
- Executable scripts: see `scripts/` directory
- Output templates/assets: see `assets/` directory
