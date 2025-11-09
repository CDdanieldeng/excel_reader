"""
表头解析器 - 多层表头展开
"""
import pandas as pd
import numpy as np
from collections import Counter
from typing import List, Dict, Tuple, Optional
from .models import HeaderHierarchy
from .config import ParserConfig
from .models import FileFormat


class HeaderParser:
    """表头解析器"""
    
    def __init__(self, config: ParserConfig, format: FileFormat):
        self.config = config
        self.format = format
    
    def parse_headers(self, df: pd.DataFrame, block, O: np.ndarray, S: np.ndarray, 
                     T: np.ndarray, merged_cells: List[Dict]) -> HeaderHierarchy:
        """
        解析表头
        返回 HeaderHierarchy
        """
        hierarchy = HeaderHierarchy()
        
        # 1. 检测表头行
        header_rows = self._detect_header_rows(df, block, O, S, T)
        hierarchy.header_rows = header_rows
        
        if not header_rows:
            # 如果没有检测到表头，使用第一行作为列名
            hierarchy.leaf_columns = [str(df.iloc[block.r0, c]) if block.r0 < df.shape[0] and c < df.shape[1] 
                                     else f"Column{c}" for c in range(block.c0, block.c1)]
            return hierarchy
        
        # 2. 构建层级映射
        header_map = self._build_header_map(df, block, header_rows, merged_cells)
        hierarchy.header_map = header_map
        
        # 3. 展开到叶子级
        hierarchy.leaf_columns = self._expand_to_leaf_columns(df, block, header_rows, header_map, merged_cells)
        
        return hierarchy
    
    def _detect_header_rows(self, df: pd.DataFrame, block, O: np.ndarray, 
                           S: np.ndarray, T: np.ndarray) -> List[int]:
        """
        检测表头行
        基于：文本比例↑、数值比例↓、样式强度↑、合并覆盖↑
        """
        header_rows = []
        max_rows_to_check = min(block.r0 + self.config.max_header_rows, block.r1, df.shape[0])
        
        for r in range(block.r0, max_rows_to_check):
            score = 0.0
            
            # 文本比例
            text_count = 0
            numeric_count = 0
            for c in range(block.c0, min(block.c1, df.shape[1])):
                if O[r, c] == 1:
                    cell_type = T[r, c] if r < T.shape[0] and c < T.shape[1] else 0
                    if cell_type == 1:  # 文本
                        text_count += 1
                    elif cell_type == 2:  # 数字
                        numeric_count += 1
            
            total = text_count + numeric_count
            if total > 0:
                text_ratio = text_count / total
                score += text_ratio * 0.4
            
            # 样式强度（xlsx 有效）
            if self.format == FileFormat.xlsx and r < S.shape[0]:
                style_score = np.mean(S[r, block.c0:min(block.c1, S.shape[1])])
                score += style_score * self.config.header_style_weight
            
            # 数值比例低
            if total > 0:
                numeric_ratio = numeric_count / total
                score += (1 - numeric_ratio) * 0.3
            
            # 合并单元格覆盖（简化：检查是否有合并单元格）
            # 这里简化处理，实际应该检查 merged_cells
            
            if score > 0.4:  # 阈值
                header_rows.append(r)
        
        return header_rows[:self.config.max_header_rows]
    
    def _build_header_map(self, df: pd.DataFrame, block, header_rows: List[int], 
                         merged_cells: List[Dict]) -> Dict[Tuple[int, int], List[str]]:
        """
        构建表头映射: (row_idx, col_idx) → 层级标题列表
        """
        header_map = {}
        
        # 构建合并单元格索引（快速查找）
        merged_index = {}
        for merged in merged_cells:
            mr0, mr1 = merged["min_row"], merged["max_row"]
            mc0, mc1 = merged["min_col"], merged["max_col"]
            for r in range(mr0, mr1 + 1):
                for c in range(mc0, mc1 + 1):
                    merged_index[(r, c)] = (mr0, mc0)  # 指向合并单元格的左上角
        
        # 对每个表头行，收集标题
        for row_idx in header_rows:
            for col_idx in range(block.c0, min(block.c1, df.shape[1])):
                # 检查是否在合并单元格内
                if (row_idx, col_idx) in merged_index:
                    # 使用合并单元格的左上角值
                    merge_r, merge_c = merged_index[(row_idx, col_idx)]
                    if merge_r < df.shape[0] and merge_c < df.shape[1]:
                        value = df.iloc[merge_r, merge_c]
                    else:
                        value = None
                else:
                    value = df.iloc[row_idx, col_idx] if row_idx < df.shape[0] and col_idx < df.shape[1] else None
                
                if pd.notna(value) and str(value).strip() != "":
                    key = (row_idx, col_idx)
                    if key not in header_map:
                        header_map[key] = []
                    header_map[key].append(str(value).strip())
        
        return header_map
    
    def _expand_to_leaf_columns(self, df: pd.DataFrame, block, header_rows: List[int],
                                header_map: Dict[Tuple[int, int], List[str]],
                                merged_cells: List[Dict]) -> List[str]:
        """
        展开到叶子级列名
        """
        leaf_columns = []
        
        # 构建合并单元格范围
        merged_ranges = {}
        for merged in merged_cells:
            mr0, mr1 = merged["min_row"], merged["max_row"]
            mc0, mc1 = merged["min_col"], merged["max_col"]
            for c in range(mc0, mc1 + 1):
                if c not in merged_ranges:
                    merged_ranges[c] = []
                merged_ranges[c].append((mr0, mr1, mc0, mc1))
        
        # 对每一列，收集所有层级的标题
        for c in range(block.c0, min(block.c1, df.shape[1])):
            column_path = []
            
            # 从最上层表头行开始，向下收集
            for row_idx in header_rows:
                # 检查该列是否在合并单元格内
                in_merged = False
                merged_value = None
                
                for merged in merged_cells:
                    mr0, mr1 = merged["min_row"], merged["max_row"]
                    mc0, mc1 = merged["min_col"], merged["max_col"]
                    if mr0 <= row_idx <= mr1 and mc0 <= c <= mc1:
                        # 使用合并单元格左上角的值
                        if mr0 < df.shape[0] and mc0 < df.shape[1]:
                            merged_value = df.iloc[mr0, mc0]
                        in_merged = True
                        break
                
                if in_merged and pd.notna(merged_value):
                    value = str(merged_value).strip()
                    if value and value not in column_path:
                        column_path.append(value)
                else:
                    # 直接读取单元格
                    if row_idx < df.shape[0] and c < df.shape[1]:
                        value = df.iloc[row_idx, c]
                        if pd.notna(value) and str(value).strip() != "":
                            value_str = str(value).strip()
                            if value_str not in column_path:
                                column_path.append(value_str)
            
            # 合并路径为列名
            if column_path:
                if self.config.keep_leaf_only:
                    # 只保留最底层（最后一个）
                    leaf_name = column_path[-1]
                else:
                    # 使用路径连接
                    leaf_name = "/".join(column_path)
            else:
                leaf_name = f"Column{c}"
            
            leaf_columns.append(leaf_name)
        
        # 处理重复列名
        leaf_columns = self._handle_duplicate_columns(leaf_columns)
        
        return leaf_columns
    
    def _handle_duplicate_columns(self, columns: List[str]) -> List[str]:
        """处理重复列名"""
        counts = Counter(columns)
        result = []
        seen = {}
        
        for col in columns:
            if counts[col] > 1:
                if col not in seen:
                    seen[col] = 0
                seen[col] += 1
                result.append(f"{col}{self.config.duplicate_col_suffix.format(n=seen[col])}")
            else:
                result.append(col)
        
        return result

