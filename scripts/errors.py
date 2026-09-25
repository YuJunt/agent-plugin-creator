#!/usr/bin/env python3
"""
统一错误码系统

为所有脚本提供标准化的错误码、错误消息和修复建议。

用法:
    from errors import ErrorCode, PluginError, format_error

    raise PluginError(ErrorCode.VALIDATION_FAILED, "详细描述")
    print(format_error(ErrorCode.VALIDATION_FAILED, "详细描述"))
"""
import json
import sys
from enum import Enum
from pathlib import Path


class ErrorCode(Enum):
    """统一错误码定义"""

    # 1xxx: 输入/参数错误
    INVALID_ARGUMENT = (1001, "无效参数", "检查命令行参数是否正确")
    MISSING_ARGUMENT = (1002, "缺少必需参数", "查看 --help 获取完整参数列表")
    INVALID_PATH = (1003, "路径无效", "检查文件/目录路径是否存在且可访问")
    FILE_NOT_FOUND = (1004, "文件不存在", "确认文件路径正确，或先创建该文件")
    DIRECTORY_NOT_FOUND = (1005, "目录不存在", "确认目录路径正确，或先创建该目录")
    INVALID_JSON = (1006, "JSON 格式无效", "检查 JSON 语法，使用 jsonlint 验证")
    INVALID_NAME = (1007, "名称不符合规范", "名称只能包含小写字母、数字、连字符")

    # 2xxx: 验证错误
    VALIDATION_FAILED = (2001, "验证失败", "运行 validate_plugin.py 查看详细错误")
    SCHEMA_MISMATCH = (2002, "Schema 版本不匹配", "确保 plugin.json 和 mcp.json 的 $schema 版本一致")
    MISSING_REQUIRED_FIELD = (2003, "缺少必需字段", "检查规范文档，补充必需字段")
    UNKNOWN_FIELD = (2004, "未知字段", "将自定义字段移到 extensions 下")
    NAME_MISMATCH = (2005, "名称与目录不一致", "确保 plugin name 与目录名一致")
    PATH_UNSAFE = (2006, "路径不安全", "所有插件内路径必须以 ./ 开头")

    # 3xxx: 安全错误
    SECURITY_AUDIT_FAILED = (3001, "安全审计失败", "运行 audit_plugin.py 查看详细问题")
    HARDCODED_SECRET = (3002, "检测到硬编码密钥", "将密钥移到环境变量或客户端配置")
    DANGEROUS_CODE = (3003, "检测到危险代码", "移除 eval/exec/shell=True 等危险调用")
    PATH_TRAVERSAL = (3004, "路径穿越风险", "检查文件操作路径，防止 ../ 逃逸")

    # 4xxx: MCP 错误
    MCP_HANDSHAKE_FAILED = (4001, "MCP 握手失败", "检查服务器命令和参数，确保 stdio 传输正确")
    MCP_TOOL_CALL_FAILED = (4002, "MCP 工具调用失败", "检查工具名称和参数是否正确")
    MCP_SERVER_NOT_FOUND = (4003, "MCP 服务器不存在", "检查 mcp.json 中的服务器配置")
    MCP_INVALID_TRANSPORT = (4004, "无效的 MCP 传输类型", "支持 stdio 和 streamable-http")

    # 5xxx: 构建/打包错误
    BUILD_FAILED = (5001, "构建失败", "检查构建日志，修复错误后重试")
    PACKAGE_FAILED = (5002, "打包失败", "检查插件结构，确保所有必需文件存在")
    DEPENDENCY_MISSING = (5003, "缺少依赖", "运行 manage_deps.py 检查并安装依赖")
    VERSION_CONFLICT = (5004, "版本冲突", "检查 plugin.json 和 CHANGELOG 的版本号一致性")

    # 6xxx: 外部工具错误
    EXTERNAL_TOOL_FAILED = (6001, "外部工具执行失败", "检查外部工具是否安装且可执行")
    GIT_OPERATION_FAILED = (6002, "Git 操作失败", "检查 Git 状态和权限")
    NETWORK_ERROR = (6003, "网络错误", "检查网络连接和代理设置")
    TIMEOUT = (6004, "操作超时", "增加超时时间或检查目标是否响应")

    # 9xxx: 未知/内部错误
    INTERNAL_ERROR = (9001, "内部错误", "这可能是 bug，请提交 issue")
    UNKNOWN_ERROR = (9999, "未知错误", "查看详细错误信息")

    def __init__(self, code: int, message: str, suggestion: str):
        self.code = code
        self.message = message
        self.suggestion = suggestion


class PluginError(Exception):
    """标准化插件错误异常"""

    def __init__(self, error_code: ErrorCode, detail: str = "", file: str = "", line: int = 0):
        self.error_code = error_code
        self.detail = detail
        self.file = file
        self.line = line
        super().__init__(self.format())

    def format(self, as_json: bool = False) -> str:
        """格式化错误信息"""
        return format_error(self.error_code, self.detail, self.file, self.line, as_json)

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "code": self.error_code.code,
            "error": self.error_code.message,
            "detail": self.detail,
            "suggestion": self.error_code.suggestion,
            "file": self.file,
            "line": self.line,
        }


def format_error(error_code: ErrorCode, detail: str = "", file: str = "", line: int = 0, as_json: bool = False) -> str:
    """格式化错误信息

    标准格式:
    [E1001] 无效参数: 详细描述
      文件: path/to/file.py:10
      建议: 检查命令行参数是否正确
    """
    if as_json:
        return json.dumps({
            "code": error_code.code,
            "error": error_code.message,
            "detail": detail,
            "suggestion": error_code.suggestion,
            "file": file,
            "line": line,
        }, ensure_ascii=False, indent=2)

    lines = [f"[E{error_code.code}] {error_code.message}"]
    if detail:
        lines[0] += f": {detail}"
    if file:
        loc = f"{file}:{line}" if line else file
        lines.append(f"  文件: {loc}")
    lines.append(f"  建议: {error_code.suggestion}")
    return "\n".join(lines)


def print_error(error_code: ErrorCode, detail: str = "", file: str = "", line: int = 0):
    """打印错误到 stderr"""
    print(format_error(error_code, detail, file, line), file=sys.stderr)


def get_error_by_code(code: int) -> ErrorCode | None:
    """根据错误码获取 ErrorCode"""
    for ec in ErrorCode:
        if ec.code == code:
            return ec
    return None


def list_all_errors() -> list:
    """列出所有错误码"""
    return [
        {"code": ec.code, "error": ec.message, "suggestion": ec.suggestion}
        for ec in ErrorCode
    ]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="统一错误码系统")
    parser.add_argument("--list", action="store_true", help="列出所有错误码")
    parser.add_argument("--lookup", type=int, help="查找指定错误码")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_all_errors(), ensure_ascii=False, indent=2))
    elif args.lookup:
        ec = get_error_by_code(args.lookup)
        if ec:
            print(format_error(ec))
        else:
            print(f"错误码 {args.lookup} 不存在")
    else:
        parser.print_help()
