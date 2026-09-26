"""数据分析 MCP 服务器（基于 FastMCP）"""
from fastmcp import FastMCP
import pandas as pd
import json
from pathlib import Path

mcp = FastMCP("analytics-engine")

@mcp.tool()
def load_csv(file_path: str, encoding: str = "auto") -> dict:
    """加载 CSV 文件，自动检测编码和分隔符"""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}
    encodings = ["utf-8", "gbk", "latin-1"] if encoding == "auto" else [encoding]
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            return {"rows": len(df), "columns": list(df.columns), "encoding": enc, "sample": df.head(3).to_dict("records")}
        except Exception:
            continue
    return {"error": "无法加载文件，请检查编码和格式"}

@mcp.tool()
def describe_data(file_path: str) -> dict:
    """获取数据基本统计信息"""
    df = pd.read_csv(file_path)
    return {
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "numeric_stats": df.describe().to_dict()
    }

@mcp.tool()
def clean_data(file_path: str, output_path: str, strategy: str = "drop") -> dict:
    """数据清洗：处理缺失值和重复行"""
    df = pd.read_csv(file_path)
    before = len(df)
    df = df.drop_duplicates()
    if strategy == "drop":
        df = df.dropna()
    elif strategy == "fill_mean":
        df = df.fillna(df.mean(numeric_only=True))
    elif strategy == "fill_median":
        df = df.fillna(df.median(numeric_only=True))
    df.to_csv(output_path, index=False)
    return {"before_rows": before, "after_rows": len(df), "output": output_path}

@mcp.tool()
def analyze(file_path: str, group_by: str = None, target: str = None) -> dict:
    """统计分析：分组统计和相关性分析"""
    df = pd.read_csv(file_path)
    result = {}
    if group_by and group_by in df.columns:
        result["group_stats"] = df.groupby(group_by).describe().to_dict()
    if target and target in df.columns:
        numeric_cols = df.select_dtypes(include=["number"]).columns
        result["correlation"] = df[numeric_cols].corr()[target].to_dict()
    return result

@mcp.tool()
def plot_chart(file_path: str, x: str, y: str, chart_type: str = "bar", output_path: str = "chart.png") -> dict:
    """生成图表：bar/line/scatter/pie"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    df = pd.read_csv(file_path)
    plt.figure(figsize=(10, 6))
    if chart_type == "bar":
        plt.bar(df[x], df[y])
    elif chart_type == "line":
        plt.plot(df[x], df[y])
    elif chart_type == "scatter":
        plt.scatter(df[x], df[y])
    elif chart_type == "pie":
        plt.pie(df[y], labels=df[x], autopct="%1.1f%%")
    plt.title(f"{y} by {x}")
    plt.xlabel(x)
    plt.ylabel(y)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    return {"chart_type": chart_type, "output": output_path, "x": x, "y": y}

if __name__ == "__main__":
    mcp.run()
