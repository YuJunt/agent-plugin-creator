# 统一日志系统使用指南

> 本指南说明如何使用 `scripts/common/logger.py` 统一日志系统。

## 概述

`scripts/common/logger.py` 提供标准化的日志输出，适用于新建脚本和需要调试的场景。现有脚本已稳定运行，可按需迁移。

## 快速开始

```python
import sys
sys.path.insert(0, str(Path(__file__).parent))

from common.logger import setup_logging, get_logger

# 初始化（verbose 模式输出 DEBUG）
setup_logging(verbose=False)

# 获取日志器
log = get_logger("my-script")

# 使用
log.debug("调试信息")      # 仅 verbose 模式输出到 stderr
log.info("普通信息")       # 输出到 stdout
log.warning("警告信息")    # 输出到 stderr
log.error("错误信息")      # 输出到 stderr
log.success("操作成功")    # ✅ 前缀
log.fail("操作失败")       # ❌ 前缀
log.step(1, 5, "第一步")   # [1/5] 前缀
```

## 日志级别

| 级别 | 输出目标 | 颜色 | 使用场景 |
|------|---------|------|---------|
| DEBUG | stderr | 青色 | 详细调试信息，仅 verbose 模式 |
| INFO | stdout | 绿色 | 正常进度信息 |
| WARNING | stderr | 黄色 | 非致命警告 |
| ERROR | stderr | 红色 | 错误，但可继续 |
| CRITICAL | stderr | 紫色 | 致命错误，需终止 |

## 命令行集成

在 argparse 中添加 --verbose 选项：

```python
import argparse
from common.logger import setup_logging, get_logger, parse_verbose_args

def main():
    # 方法1：手动解析
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    
    # 方法2：自动解析（在 argparse 之前）
    argv, verbose = parse_verbose_args(sys.argv[1:])
    setup_logging(verbose=verbose)
```

## 输出格式

```
[INFO] 14:30:25 my-script - 开始处理
[WARNING] 14:30:26 my-script - 配置文件不存在，使用默认值
[ERROR] 14:30:27 my-script - 处理失败
✅ [INFO] 14:30:28 my-script - 操作成功
```

彩色终端环境下，级别标签会有对应颜色。

## 迁移指南

现有脚本迁移到统一日志系统的步骤：

1. **添加导入**：
   ```python
   from common.logger import setup_logging, get_logger
   ```

2. **初始化**：在 main() 开头添加：
   ```python
   setup_logging(verbose=args.verbose)
   log = get_logger("script-name")
   ```

3. **替换 print**：
   - `print("信息")` → `log.info("信息")`
   - `print("错误", file=sys.stderr)` → `log.error("错误")`
   - `print("✅ 成功")` → `log.success("成功")`

4. **添加 --verbose 参数**：
   ```python
   parser.add_argument("--verbose", "-v", action="store_true", help="启用调试模式")
   ```

## 注意事项

- **零依赖**：仅使用 Python 标准库（sys, time）
- **向后兼容**：不使用日志系统的脚本不受影响
- **彩色自动检测**：非终端环境（如 CI）自动禁用彩色
- **stderr/stdout 分离**：INFO 到 stdout，WARNING/ERROR/DEBUG 到 stderr
- **性能**：DEBUG 级别在非 verbose 模式下完全不执行格式化

## 最佳实践

1. **新建脚本必须使用**统一日志系统
2. **现有脚本按需迁移**，优先迁移复杂脚本（wizard, plugin_to_skill）
3. **错误必须用 log.error**，不要用 print 到 stderr
4. **成功消息用 log.success**，保持一致性
5. **多步骤操作用 log.step**，显示进度
