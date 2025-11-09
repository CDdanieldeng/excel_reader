"""
数据类与枚举定义
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Literal, Any
from enum import Enum

# ========== 枚举 ==========
class FileFormat(str, Enum):
    xlsx = "xlsx"
    xlsb = "xlsb"
    csv = "csv"


class LogLevel(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARN = "WARN"
    ERROR = "ERROR"


class ErrorCode(str, Enum):
    INVALID_ARGUMENT = "InvalidArgumentError"
    UNSUPPORTED_FORMAT = "UnsupportedFormatError"
    FILE_READ = "FileReadError"
    OUTPUT_WRITE = "OutputWriteError"


class WarningCode(str, Enum):
    MID_HEADERS_REMOVED = "MidHeadersRemoved"
    DATE_PARSE_FALLBACK = "DateParseFallback"
    UNIT_CONFLICT = "UnitConflict"
    DUPLICATE_COLUMNS = "DuplicateColumns"
    SPARSE_BLOCK_SKIPPED = "SparseBlockSkipped"
    AMBIGUOUS_MERGE_SKIP = "AmbiguousMergeSkip"


# ========== 元数据 ==========
@dataclass
class HeaderHierarchy:
    """
    header_map: (row_idx, col_idx) → 层级标题列表（自上而下）。
    leaf_columns: 解析后叶子列名（与 DataFrame 列一一对应）。
    """
    header_rows: List[int] = field(default_factory=list)
    header_map: Dict[Tuple[int, int], List[str]] = field(default_factory=dict)
    leaf_columns: List[str] = field(default_factory=list)


@dataclass
class TableScore:
    area: int = 0
    density: float = 0.0
    type_consistency: float = 0.0
    border_completeness: float = 0.0
    header_completeness: float = 0.0
    total: float = 0.0   # 综合评分


@dataclass
class TableMeta:
    source_file: str
    format: FileFormat
    sheet: Optional[str]          # csv 为 None
    bbox: Tuple[int, int, int, int]   # (r0, r1, c0, c1) 半开或闭区需在实现中统一
    is_main: bool
    score: TableScore = field(default_factory=TableScore)
    header: HeaderHierarchy = field(default_factory=HeaderHierarchy)
    merged_from: List[str] = field(default_factory=list)  # 合并来源的块 ID（可选）
    units: Optional[str] = None
    notes: Optional[str] = None
    csv_path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)     # WarningCode/自由文案


# ========== Manifest（运行清单）==========
@dataclass
class OutputItem:
    key: str                 # df1/df2/...
    name: str                # 表名（清洗后）
    csv: Optional[str]       # 实际导出路径（相对 run 根目录）
    rows: int
    cols: int


@dataclass
class Manifest:
    run_id: str
    source: str
    format: FileFormat
    sheets: Optional[List[str]]  # csv: None
    config_profile: str          # 如 "default" / "custom"
    outputs: List[OutputItem] = field(default_factory=list)
    warnings: Dict[str, int] = field(default_factory=dict)  # WarningCode -> count
    started_at_utc: str = ""       # ISO8601
    finished_at_utc: str = ""


# ========== 日志事件 ==========
@dataclass
class LogEvent:
    ts: str                 # "2025-11-09T14:30:12Z"
    lvl: LogLevel           # 固定 INFO（可临时改 DEBUG）
    event: str              # 例如: "run.start","grid.build","split.blocks","export.csv"
    file: Optional[str] = None
    format: Optional[FileFormat] = None
    sheet: Optional[str] = None
    block_id: Optional[str] = None
    message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    error_code: Optional[ErrorCode] = None
    warning_code: Optional[WarningCode] = None

