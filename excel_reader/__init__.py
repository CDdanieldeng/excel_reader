"""
Excel Reader - 自动化表格结构识别与数据抽取系统
"""

__version__ = "1.0.0"

from .parser import parse_file
from .config import ParserConfig
from .models import (
    FileFormat,
    LogLevel,
    ErrorCode,
    WarningCode,
    HeaderHierarchy,
    TableScore,
    TableMeta,
    Manifest,
    OutputItem,
)

__all__ = [
    "parse_file",
    "ParserConfig",
    "FileFormat",
    "LogLevel",
    "ErrorCode",
    "WarningCode",
    "HeaderHierarchy",
    "TableScore",
    "TableMeta",
    "Manifest",
    "OutputItem",
]

