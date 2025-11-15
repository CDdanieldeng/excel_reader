"""
配置类定义
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Literal
from .models import LogLevel
from .constants import (
    CSV_ENCODING,
    DEFAULT_MIN_BLOCK_HEIGHT,
    DEFAULT_MIN_BLOCK_WIDTH,
    DEFAULT_HOLE_TOLERANCE_ROWS,
    DEFAULT_HOLE_TOLERANCE_COLS,
    DEFAULT_DENSITY_THRESHOLD,
    DEFAULT_RECTANGULARITY_THRESHOLD,
    DEFAULT_MDL_WEIGHTS,
    DEFAULT_MERGE_GAIN_THRESHOLD,
    DEFAULT_MAX_HEADER_ROWS,
    DEFAULT_HEADER_STYLE_WEIGHT,
    DEFAULT_DUPLICATE_COL_SUFFIX,
)


@dataclass
class ParserConfig:
    # 分割参数
    min_block_height: int = DEFAULT_MIN_BLOCK_HEIGHT
    min_block_width: int = DEFAULT_MIN_BLOCK_WIDTH
    hole_tolerance_rows: int = DEFAULT_HOLE_TOLERANCE_ROWS
    hole_tolerance_cols: int = DEFAULT_HOLE_TOLERANCE_COLS
    density_threshold: float = DEFAULT_DENSITY_THRESHOLD
    rectangularity_threshold: float = DEFAULT_RECTANGULARITY_THRESHOLD
    mdl_weights: Tuple[float, float, float] = DEFAULT_MDL_WEIGHTS  # α, β, γ
    merge_gain_threshold: float = DEFAULT_MERGE_GAIN_THRESHOLD

    # 表头解析
    max_header_rows: int = DEFAULT_MAX_HEADER_ROWS
    header_style_weight: float = DEFAULT_HEADER_STYLE_WEIGHT      # xlsx 有效；xlsb/csv 降权到 0~0.1
    keep_leaf_only: bool = True
    duplicate_col_suffix: str = DEFAULT_DUPLICATE_COL_SUFFIX

    # 导出
    csv_encoding: str = CSV_ENCODING
    csv_index: bool = False
    csv_na_rep: str = ""
    sanitize_file_name: bool = True
    long_path_support: bool = True

    # 行为
    include_hidden: bool = False
    allow_mid_headers: bool = True
    unit_line_patterns: List[str] = field(default_factory=lambda: [
        r'^\s*单位[:：]\s*.*$', r'^\s*\(单位.*\)\s*$'
    ])
    csv_injection_protection: bool = False  # 默认关闭

    # 日志
    log_level: LogLevel = LogLevel.INFO
    timestamp_tz: Literal["UTC"] = "UTC"
    
    # 性能优化参数
    max_rows: int = 100000  # 最大读取行数，超过会截断
    max_cols: int = 500  # 最大读取列数，超过会截断
    max_file_size_mb: float = 100.0  # 最大文件大小（MB），超过会警告
    enable_style_scan: bool = True  # 是否扫描样式（大文件可关闭以提升性能）
    enable_border_scan: bool = True  # 是否扫描边框（大文件可关闭以提升性能）
    style_scan_limit_rows: int = 10000  # 样式扫描的行数限制（只扫描前N行）
    border_scan_limit_rows: int = 10000  # 边框扫描的行数限制（只扫描前N行）
    process_sheets_sequentially: bool = True  # 是否逐个处理 sheet（减少内存占用）

