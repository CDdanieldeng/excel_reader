"""
主解析器 - 统一入口函数
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from .file_reader import read_file, detect_format
from .grid_builder import GridBuilder
from .block_splitter import BlockSplitter, Block
from .header_parser import HeaderParser
from .cleaner import Cleaner
from .logger import DualLogger
from .exporter import Exporter
from .models import FileFormat, TableMeta, TableScore, HeaderHierarchy, Manifest, OutputItem, WarningCode, LogLevel
from .config import ParserConfig
from .constants import RUN_ID_FORMAT, RUN_TS_FORMAT, DIR_LOGS
from .exceptions import InvalidArgumentError, OutputWriteError


def parse_file(
    file_path: str,
    sheet_name: Optional[List[str]] = None,
    output_dir: str = "outputs",
    export_csv: bool = True,
    config: Optional[ParserConfig] = None
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, TableMeta]]:
    """
    统一入口函数：解析 Excel/CSV 文件
    
    Args:
        file_path: 输入文件路径
        sheet_name: Sheet 名称列表（xlsx/xlsb 必填，csv 必须为 None）
        output_dir: 输出目录
        export_csv: 是否导出 CSV
        config: 配置对象
    
    Returns:
        (DataFrames字典, TableMeta字典)
    """
    if config is None:
        config = ParserConfig()
    
    # 1. 参数验证
    file_format = detect_format(file_path)
    if file_format == FileFormat.csv:
        if sheet_name is not None and len(sheet_name) > 0:
            raise InvalidArgumentError("sheet_name must be None or empty for CSV files")
        sheet_name = None
    else:
        if not sheet_name or len(sheet_name) == 0:
            raise InvalidArgumentError("sheet_name is required for xlsx/xlsb files")
    
    # 2. 创建运行目录
    run_timestamp = datetime.now(timezone.utc)
    ts_str = run_timestamp.strftime(RUN_TS_FORMAT)
    run_id = f"RUN_{ts_str}_UTC"
    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. 初始化日志
    log_dir = run_dir / DIR_LOGS
    logger = DualLogger(log_dir, config.log_level)
    
    try:
        logger.log("run.start", file=Path(file_path).name, format=file_format)
        
        # 4. 读取文件
        sheet_data = read_file(file_path, sheet_name, file_format, config.include_hidden)
        logger.log("file.loaded", file=Path(file_path).name, format=file_format,
                  metrics={"sheets": list(sheet_data.keys())})
        
        # 5. 处理每个 sheet
        all_dfs = {}
        all_metas = {}
        df_counter = 1
        
        for sheet_name_key, (df_raw, metadata) in sheet_data.items():
            logger.log("grid.build", sheet=sheet_name_key if sheet_name_key != "__csv__" else None,
                      metrics={"cells_total": df_raw.size, "nonempty": df_raw.notna().sum().sum()})
            
            # 构建网格
            grid_builder = GridBuilder(df_raw, metadata, file_format)
            O = grid_builder.build_occupancy_matrix()
            B = grid_builder.build_border_matrix() if file_format == FileFormat.xlsx else None
            S = grid_builder.build_style_matrix()
            T = grid_builder.build_type_matrix()
            merged_cells = grid_builder.get_merged_cells()
            
            # 分割表块
            splitter = BlockSplitter(config, file_format)
            blocks = splitter.split_blocks(O, B)
            logger.log("split.blocks", sheet=sheet_name_key if sheet_name_key != "__csv__" else None,
                      metrics={"count": len(blocks), 
                              "sizes": [[b.height, b.width] for b in blocks]})
            
            if not blocks:
                continue
            
            # 处理每个块
            cleaner = Cleaner(config)
            header_parser = HeaderParser(config, file_format)
            scores = {}
            header_hierarchies = {}
            
            # 先解析所有块的表头
            for block in blocks:
                header_hierarchy = header_parser.parse_headers(
                    df_raw, block, O, S, T, merged_cells
                )
                header_hierarchies[block.block_id] = header_hierarchy
            
            # 计算每个块的评分（使用表头信息）
            for block in blocks:
                header_hierarchy = header_hierarchies[block.block_id]
                score = cleaner.calculate_table_score(
                    block, O, T, B, header_hierarchy.header_rows
                )
                scores[block.block_id] = score
            
            # 识别主表
            main_block_id = cleaner.identify_main_table(blocks, scores)
            
            # 处理每个块
            for block in blocks:
                # 提取块数据
                df_block = df_raw.iloc[block.r0:block.r1, block.c0:block.c1].copy()
                
                # 获取已解析的表头
                header_hierarchy = header_hierarchies[block.block_id]
                logger.log("header.detect", 
                          sheet=sheet_name_key if sheet_name_key != "__csv__" else None,
                          block_id=block.block_id,
                          metrics={"header_rows": header_hierarchy.header_rows,
                                  "leaf_cols": len(header_hierarchy.leaf_columns)})
                
                # 设置列名
                if header_hierarchy.leaf_columns:
                    df_block.columns = header_hierarchy.leaf_columns[:len(df_block.columns)]
                    # 移除表头行
                    if header_hierarchy.header_rows:
                        header_row_indices = [r - block.r0 for r in header_hierarchy.header_rows 
                                            if block.r0 <= r < block.r1]
                        if header_row_indices:
                            df_block = df_block.drop(df_block.index[header_row_indices])
                            df_block.reset_index(drop=True, inplace=True)
                
                # 清洗数据
                df_cleaned, unit_str, removed_rows = cleaner.clean_dataframe(
                    df_block, header_hierarchy.header_rows, config.unit_line_patterns
                )
                if removed_rows:
                    logger.log("clean.mid_headers_removed",
                              warning_code=WarningCode.MID_HEADERS_REMOVED,
                              metrics={"rows": removed_rows})
                
                # 构建 TableMeta
                meta = TableMeta(
                    source_file=file_path,
                    format=file_format,
                    sheet=sheet_name_key if sheet_name_key != "__csv__" else None,
                    bbox=(block.r0, block.r1, block.c0, block.c1),
                    is_main=(block.block_id == main_block_id),
                    score=scores.get(block.block_id, TableScore()),
                    header=header_hierarchy,
                    units=unit_str,
                )
                
                # 导出 CSV
                csv_path = None
                if export_csv:
                    exporter = Exporter(run_dir, config)
                    table_name = sheet_name_key if sheet_name_key != "__csv__" else "table"
                    csv_path = exporter.export_csv(df_cleaned, table_name, run_timestamp)
                    meta.csv_path = str(csv_path)
                    logger.log("export.csv", 
                              message=f"df{df_counter} exported",
                              file=str(csv_path),
                              metrics={"rows": len(df_cleaned), "cols": len(df_cleaned.columns)})
                
                # 存储
                df_key = f"df{df_counter}"
                all_dfs[df_key] = df_cleaned
                all_metas[df_key] = meta
                df_counter += 1
        
        # 6. 导出元数据
        if all_metas:
            exporter = Exporter(run_dir, config)
            exporter.export_metadata(all_metas)
        
        # 7. 生成 Manifest
        manifest = Manifest(
            run_id=run_id,
            source=file_path,
            format=file_format,
            sheets=sheet_name if file_format != FileFormat.csv else None,
            config_profile="default",
            started_at_utc=run_timestamp.isoformat().replace("+00:00", "Z"),
            finished_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            outputs=[
                OutputItem(
                    key=key,
                    name=meta.sheet or "table",
                    csv=str(meta.csv_path) if meta.csv_path else None,
                    rows=len(df),
                    cols=len(df.columns)
                )
                for key, (df, meta) in zip(all_dfs.keys(), zip(all_dfs.values(), all_metas.values()))
            ],
        )
        
        exporter = Exporter(run_dir, config)
        exporter.export_manifest(manifest)
        
        logger.log("run.end", message="Run completed successfully")
        
        return all_dfs, all_metas
    
    except Exception as e:
        logger.log("error", level=LogLevel.ERROR, message=str(e))
        raise
    finally:
        logger.close()

