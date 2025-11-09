"""
导出系统 - CSV导出和Manifest生成
"""
import pandas as pd
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from .models import TableMeta, Manifest, OutputItem, FileFormat
from .constants import (
    CSV_ENCODING, CSV_DELIMITER, CSV_LINE_TERMINATOR,
    INVALID_FILENAME_CHARS, RUN_TS_FORMAT, DIR_CSV, DIR_ARTIFACTS
)
from .exceptions import OutputWriteError


class Exporter:
    """导出器"""
    
    def __init__(self, run_dir: Path, config):
        self.run_dir = run_dir
        self.config = config
        self.csv_dir = run_dir / DIR_CSV
        self.artifacts_dir = run_dir / DIR_ARTIFACTS
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def export_csv(self, df: pd.DataFrame, table_name: str, 
                   timestamp: datetime) -> Path:
        """
        导出 CSV 文件
        返回: 相对 run_dir 的路径
        """
        # 清洗文件名
        safe_name = self._sanitize_filename(table_name)
        
        # 生成时间戳字符串
        ts_str = timestamp.strftime(RUN_TS_FORMAT)
        
        # 构建文件名
        filename = f"{safe_name}_{ts_str}.csv"
        
        # 检查冲突并处理
        csv_path = self.csv_dir / filename
        counter = 1
        while csv_path.exists():
            base_name = safe_name
            if base_name.endswith(f"_dup{counter - 1}"):
                base_name = base_name.rsplit("_dup", 1)[0]
            filename = f"{base_name}_dup{counter}_{ts_str}.csv"
            csv_path = self.csv_dir / filename
            counter += 1
        
        # 导出 CSV
        try:
            df.to_csv(
                csv_path,
                encoding=self.config.csv_encoding,
                index=self.config.csv_index,
                na_rep=self.config.csv_na_rep,
                sep=CSV_DELIMITER,
                lineterminator=CSV_LINE_TERMINATOR
            )
        except Exception as e:
            raise OutputWriteError(f"Failed to export CSV: {str(e)}")
        
        # 返回相对路径
        return csv_path.relative_to(self.run_dir)
    
    def export_metadata(self, metas: Dict[str, TableMeta]):
        """
        导出元数据 JSON
        """
        metadata_dict = {}
        for key, meta in metas.items():
            metadata_dict[key] = {
                "source_file": meta.source_file,
                "format": meta.format.value,
                "sheet": meta.sheet,
                "bbox": list(meta.bbox),
                "is_main": meta.is_main,
                "score": {
                    "area": meta.score.area,
                    "density": meta.score.density,
                    "type_consistency": meta.score.type_consistency,
                    "border_completeness": meta.score.border_completeness,
                    "header_completeness": meta.score.header_completeness,
                    "total": meta.score.total,
                },
                "header": {
                    "header_rows": meta.header.header_rows,
                    "leaf_columns": meta.header.leaf_columns,
                },
                "csv_path": str(meta.csv_path) if meta.csv_path else None,
                "warnings": meta.warnings,
                "units": meta.units,
                "notes": meta.notes,
            }
        
        metadata_path = self.artifacts_dir / "tables_meta.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise OutputWriteError(f"Failed to export metadata: {str(e)}")
    
    def export_manifest(self, manifest: Manifest):
        """
        导出 Manifest YAML
        """
        manifest_path = self.run_dir / "manifest.yml"
        
        manifest_dict = {
            "run_id": manifest.run_id,
            "source": manifest.source,
            "format": manifest.format.value,
            "sheets": manifest.sheets,
            "config_profile": manifest.config_profile,
            "started_at_utc": manifest.started_at_utc,
            "finished_at_utc": manifest.finished_at_utc,
            "outputs": [
                {
                    "key": item.key,
                    "name": item.name,
                    "csv": item.csv,
                    "rows": item.rows,
                    "cols": item.cols,
                }
                for item in manifest.outputs
            ],
            "warnings": manifest.warnings,
        }
        
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                yaml.dump(manifest_dict, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            raise OutputWriteError(f"Failed to export manifest: {str(e)}")
    
    def _sanitize_filename(self, name: str) -> str:
        """
        清洗文件名：去除非法字符
        """
        if not self.config.sanitize_file_name:
            return name
        
        # 替换非法字符
        for char in INVALID_FILENAME_CHARS:
            name = name.replace(char, "_")
        
        # 去除首尾空白
        name = name.strip()
        
        # 限制长度
        if self.config.long_path_support:
            max_len = 200
        else:
            max_len = 120
        
        if len(name) > max_len:
            name = name[:max_len]
        
        # 如果为空，使用默认名
        if not name:
            name = "table"
        
        return name

