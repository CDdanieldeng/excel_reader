# Excel Reader - 自动化表格结构识别与数据抽取系统

**版本**：v1.0  
**更新时间**：2025-11-09（UTC）

## 项目简介

这是一个自动化表格结构识别与数据抽取系统，能够智能处理 Excel 文件（`.xlsx`、`.xlsb`）和 CSV 文件，自动识别表格结构、解析多层表头、分割表块，并输出标准化的数据。

## 核心功能

- ✅ 统一入口函数 `parse_file()`，支持 `.xlsx`、`.xlsb`、`.csv` 文件
- ✅ 自动识别主表格与小表格
- ✅ 智能解析多层表头，保留最细粒度（叶子）表头
- ✅ 鲁棒分割与并表判断
- ✅ 输出标准化的 `pandas.DataFrame` 和 UTF-8 CSV 文件
- ✅ 完整的日志记录（文本与 JSONL 格式）

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

```python
from excel_reader import parse_file, ParserConfig

# 解析 Excel 文件
dfs, metas = parse_file(
    file_path="inputs/本月报表.xlsx",
    sheet_name=["财务数据", "销售表"],
    output_dir="outputs",
    export_csv=True,
    config=ParserConfig()
)

# 访问解析后的数据
for key, df in dfs.items():
    print(f"{key}: {df.shape}")
    print(df.head())
```

## 输出结构

```
outputs/
  └─ RUN_YYYYMMDD_HHMMSS_UTC/
       ├─ csv/
       │    ├─ 表1_YYYYMMDD_HHMMSS.csv
       │    └─ 表2_YYYYMMDD_HHMMSS.csv
       ├─ logs/
       │    ├─ run.log.txt
       │    └─ run.log.jsonl
       ├─ artifacts/
       │    └─ tables_meta.json
       └─ manifest.yml
```

## 配置选项

```python
from excel_reader import ParserConfig

config = ParserConfig(
    # 分割参数
    min_block_height=3,
    min_block_width=3,
    density_threshold=0.35,
    
    # 表头解析
    max_header_rows=6,
    keep_leaf_only=True,
    
    # 导出
    csv_encoding="utf-8",
    csv_index=False,
)
```

## 系统架构

1. **文件读取器**：支持 xlsx/xlsb/csv 格式
2. **网格构建器**：构建占用矩阵、边框图、样式图
3. **表块分割器**：基于连通域检测和 MDL 代价函数
4. **表头解析器**：多层表头展开
5. **清洗器**：并表判定、重复表头移除
6. **导出器**：CSV 导出和 Manifest 生成

## 算法说明

### 表块分割

- 构建占用矩阵，识别非空单元格
- 连通域检测，容忍空洞
- MDL 代价函数决策是否拆分

### 表头识别

- 基于文本比例、数值比例、样式强度检测表头行
- 展开多层合并单元格到叶子级
- 处理重复列名

### 并表判定

- 计算列对齐度、类型一致度、密度变化
- 使用增益函数判断是否合并

## 日志系统

所有日志采用 UTC 时间戳，支持文本和 JSONL 两种格式：

```
[2025-11-09T14:30:12Z INFO] run.start file=本月报表.xlsx format=xlsx
[2025-11-09T14:30:15Z INFO] split.blocks sheet=财务数据 count=3
[2025-11-09T14:30:19Z INFO] export.csv df1 exported rows=1024 cols=12
```

## 异常处理

系统定义了以下异常类型：

- `InvalidArgumentError`: 参数错误
- `UnsupportedFormatError`: 不支持的文件格式
- `FileReadError`: 文件读取失败
- `OutputWriteError`: 输出写入失败

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

