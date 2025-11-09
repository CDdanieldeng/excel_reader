"""
日志系统 - 文本和JSONL格式
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from .models import LogEvent, LogLevel, FileFormat, ErrorCode, WarningCode


class DualLogger:
    """双格式日志记录器（文本 + JSONL）"""
    
    def __init__(self, log_dir: Path, log_level: LogLevel = LogLevel.INFO):
        self.log_dir = log_dir
        self.log_level = log_level
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 文本日志
        self.txt_logger = logging.getLogger("excel_reader_txt")
        self.txt_logger.setLevel(logging.INFO)
        txt_handler = logging.FileHandler(log_dir / "run.log.txt", encoding="utf-8")
        txt_handler.setFormatter(logging.Formatter(
            "[%(asctime)s %(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        ))
        self.txt_logger.addHandler(txt_handler)
        
        # JSONL 日志
        self.jsonl_path = log_dir / "run.log.jsonl"
        self.jsonl_file = open(self.jsonl_path, "w", encoding="utf-8")
    
    def log(self, event: str, level: LogLevel = LogLevel.INFO, file: Optional[str] = None,
            format: Optional[FileFormat] = None, sheet: Optional[str] = None,
            block_id: Optional[str] = None, message: Optional[str] = None,
            metrics: Optional[Dict[str, Any]] = None,
            error_code: Optional[ErrorCode] = None,
            warning_code: Optional[WarningCode] = None):
        """
        记录日志事件
        """
        # 生成 UTC 时间戳
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # 构建日志事件
        log_event = LogEvent(
            ts=ts,
            lvl=level,
            event=event,
            file=file,
            format=format,
            sheet=sheet,
            block_id=block_id,
            message=message,
            metrics=metrics,
            error_code=error_code,
            warning_code=warning_code
        )
        
        # 写入 JSONL
        json_obj = {
            "ts": log_event.ts,
            "lvl": log_event.lvl.value,
            "event": log_event.event,
        }
        if log_event.file:
            json_obj["file"] = log_event.file
        if log_event.format:
            json_obj["format"] = log_event.format.value
        if log_event.sheet:
            json_obj["sheet"] = log_event.sheet
        if log_event.block_id:
            json_obj["block_id"] = log_event.block_id
        if log_event.message:
            json_obj["message"] = log_event.message
        if log_event.metrics:
            # 转换 numpy/pandas 类型为 Python 原生类型
            json_obj["metrics"] = self._convert_to_json_serializable(log_event.metrics)
        if log_event.error_code:
            json_obj["error_code"] = log_event.error_code.value
        if log_event.warning_code:
            json_obj["warning_code"] = log_event.warning_code.value
        
        self.jsonl_file.write(json.dumps(json_obj, ensure_ascii=False) + "\n")
        self.jsonl_file.flush()
        
        # 写入文本日志
        parts = [f"{log_event.event}"]
        if log_event.file:
            parts.append(f"file={log_event.file}")
        if log_event.format:
            parts.append(f"format={log_event.format.value}")
        if log_event.sheet:
            parts.append(f"sheet={log_event.sheet}")
        if log_event.block_id:
            parts.append(f"block_id={log_event.block_id}")
        if log_event.message:
            parts.append(log_event.message)
        if log_event.metrics:
            # 转换 metrics 中的值以便正确格式化
            metrics_converted = self._convert_to_json_serializable(log_event.metrics)
            metrics_str = " ".join(f"{k}={v}" for k, v in metrics_converted.items())
            if metrics_str:
                parts.append(metrics_str)
        
        msg = " ".join(parts)
        
        if level == LogLevel.ERROR:
            self.txt_logger.error(msg)
        elif level == LogLevel.WARN:
            self.txt_logger.warning(msg)
        else:
            self.txt_logger.info(msg)
    
    def _convert_to_json_serializable(self, obj):
        """
        将 numpy/pandas 类型转换为 JSON 可序列化的 Python 原生类型
        """
        import numpy as np
        import pandas as pd
        
        if isinstance(obj, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            # 尝试直接转换（适用于 numpy 标量类型）
            try:
                if hasattr(obj, 'item'):  # numpy 标量有 item() 方法
                    return obj.item()
            except (ValueError, AttributeError):
                pass
            return obj
    
    def close(self):
        """关闭日志文件"""
        if self.jsonl_file:
            self.jsonl_file.close()

