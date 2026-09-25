#!/usr/bin/env python3
"""
进度可视化工具模块

提供可复用的进度条、步骤指示器、计时器等功能。

用法:
    from progress import ProgressBar, StepIndicator, Timer

    # 进度条
    bar = ProgressBar(total=10, prefix="处理中")
    for i in range(10):
        bar.update(f"步骤 {i+1}")
    bar.done()

    # 步骤指示器
    steps = StepIndicator(["采集", "处理", "验证", "输出"])
    steps.start("采集")
    # ... 做事情 ...
    steps.next("处理")
    steps.complete()

    # 计时器
    with Timer("任务名") as t:
        # ... 做事情 ...
        pass
    print(f"耗时: {t.elapsed:.1f}s")
"""
import sys
import time
from contextlib import contextmanager


class ProgressBar:
    """终端进度条"""

    def __init__(self, total: int, prefix: str = "", width: int = 40, stream=None):
        self.total = max(1, total)
        self.current = 0
        self.prefix = prefix
        self.width = width
        self.stream = stream or sys.stdout
        self.start_time = time.time()
        self._closed = False

    def update(self, step: str = "", increment: int = 1):
        """更新进度"""
        self.current = min(self.total, self.current + increment)
        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = "█" * filled + "░" * (self.width - filled)
        elapsed = time.time() - self.start_time
        eta = elapsed / pct - elapsed if pct > 0 else 0

        if step:
            line = f"\r{self.prefix} [{bar}] {self.current}/{self.total} ({pct*100:.0f}%) {step} ETA:{eta:.0f}s"
        else:
            line = f"\r{self.prefix} [{bar}] {self.current}/{self.total} ({pct*100:.0f}%) ETA:{eta:.0f}s"

        self.stream.write(line)
        self.stream.flush()

        if self.current >= self.total:
            self.done()

    def done(self):
        """完成进度条"""
        if self._closed:
            return
        self._closed = True
        elapsed = time.time() - self.start_time
        bar = "█" * self.width
        line = f"\r{self.prefix} [{bar}] {self.total}/{self.total} (100%) 完成 ({elapsed:.1f}s)"
        self.stream.write(line + "\n")
        self.stream.flush()


class StepIndicator:
    """步骤指示器"""

    def __init__(self, steps: list, prefix: str = "", stream=None):
        self.steps = steps
        self.current_index = -1
        self.prefix = prefix
        self.stream = stream or sys.stdout
        self.start_time = None
        self.step_start_time = None

    def start(self, step_name: str = None):
        """开始第一个步骤"""
        self.current_index = 0
        self.start_time = time.time()
        self.step_start_time = time.time()
        name = step_name or self.steps[0]
        self._print_step(name, "start")

    def next(self, step_name: str = None):
        """完成当前步骤，进入下一步"""
        if self.current_index >= 0:
            elapsed = time.time() - self.step_start_time
            self._print_step(self.steps[self.current_index], "done", elapsed)

        self.current_index += 1
        if self.current_index < len(self.steps):
            self.step_start_time = time.time()
            name = step_name or self.steps[self.current_index]
            self._print_step(name, "start")
        else:
            self.complete()

    def fail(self, reason: str = ""):
        """标记当前步骤失败"""
        if self.current_index >= 0:
            elapsed = time.time() - self.step_start_time
            name = self.steps[self.current_index]
            self.stream.write(f"  ❌ {name} 失败 ({elapsed:.1f}s)")
            if reason:
                self.stream.write(f": {reason}")
            self.stream.write("\n")
            self.stream.flush()

    def complete(self):
        """全部完成"""
        total = time.time() - self.start_time if self.start_time else 0
        self.stream.write(f"\n✅ 全部完成 ({total:.1f}s)\n")
        self.stream.flush()

    def _print_step(self, name: str, status: str, elapsed: float = 0):
        if status == "start":
            self.stream.write(f"  🔄 {name}...\n")
        elif status == "done":
            self.stream.write(f"  ✅ {name} ({elapsed:.1f}s)\n")
        self.stream.flush()


class Timer:
    """计时器（上下文管理器）"""

    def __init__(self, name: str = "", stream=None):
        self.name = name
        self.stream = stream or sys.stdout
        self.elapsed = 0
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        if self.name:
            self.stream.write(f"  ⏱️  {self.name}...\n")
            self.stream.flush()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        if self.name:
            self.stream.write(f"  ✅ {self.name} 完成 ({self.elapsed:.1f}s)\n")
            self.stream.flush()


class Spinner:
    """加载旋转指示器"""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, text: str = "", stream=None):
        self.text = text
        self.stream = stream or sys.stdout
        self._running = False
        self._frame = 0

    def update(self, text: str = None):
        """更新旋转帧"""
        if text:
            self.text = text
        frame = self.FRAMES[self._frame % len(self.FRAMES)]
        self._frame += 1
        self.stream.write(f"\r{frame} {self.text}")
        self.stream.flush()

    def done(self, success: bool = True):
        """完成"""
        icon = "✅" if success else "❌"
        self.stream.write(f"\r{icon} {self.text}\n")
        self.stream.flush()


def print_section(title: str, stream=None):
    """打印分节标题"""
    s = stream or sys.stdout
    s.write(f"\n{'='*50}\n")
    s.write(f"  {title}\n")
    s.write(f"{'='*50}\n")
    s.flush()


def print_result(name: str, passed: bool, detail: str = "", stream=None):
    """打印检查结果"""
    s = stream or sys.stdout
    icon = "✅" if passed else "❌"
    line = f"  {icon} {name}"
    if detail:
        line += f" — {detail}"
    s.write(line + "\n")
    s.flush()


if __name__ == "__main__":
    # 演示
    print_section("进度可视化演示")

    print("\n进度条:")
    bar = ProgressBar(total=5, prefix="处理")
    for i in range(5):
        time.sleep(0.1)
        bar.update(f"项目 {i+1}")

    print("\n步骤指示器:")
    steps = StepIndicator(["采集数据", "处理数据", "验证结果", "生成报告"])
    steps.start()
    time.sleep(0.1)
    steps.next()
    time.sleep(0.1)
    steps.next()
    time.sleep(0.1)
    steps.next()
    steps.complete()

    print("\n计时器:")
    with Timer("示例任务"):
        time.sleep(0.1)

    print("\n检查结果:")
    print_result("规范验证", True)
    print_result("安全审计", True, "0 critical, 0 high")
    print_result("性能测试", False, "超时 15s")
