"""
清洗与合并逻辑
"""
import pandas as pd
import numpy as np
import re
from collections import Counter
from typing import List, Dict, Tuple, Optional
from .models import TableScore, WarningCode
from .block_splitter import Block
from .config import ParserConfig


class Cleaner:
    """数据清洗器"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
    
    def calculate_table_score(self, block: Block, O: np.ndarray, T: np.ndarray, 
                             B: np.ndarray = None, header_rows: List[int] = None) -> TableScore:
        """
        计算表块评分
        """
        score = TableScore()
        
        # 面积
        score.area = block.area
        
        # 密度
        block_region = O[block.r0:block.r1, block.c0:block.c1]
        score.density = float(np.sum(block_region)) / max(block.area, 1)
        
        # 类型一致性（同一列类型应该一致）
        type_consistency = 0.0
        for c in range(block.c0, block.c1):
            col_types = []
            for r in range(block.r0, block.r1):
                if r < T.shape[0] and c < T.shape[1]:
                    col_types.append(T[r, c])
            if col_types:
                # 计算最常见的类型占比
                most_common_count = Counter(col_types).most_common(1)[0][1]
                type_consistency += most_common_count / len(col_types)
        type_consistency /= max(block.width, 1)
        score.type_consistency = type_consistency
        
        # 边框完整性
        if B is not None:
            border_count = 0
            total_edges = 0
            for r in range(block.r0, block.r1):
                for c in range(block.c0, block.c1):
                    if r < B.shape[0] and c < B.shape[1]:
                        borders = B[r, c]
                        if r == block.r0:
                            border_count += borders[0]  # top
                        if r == block.r1 - 1:
                            border_count += borders[2]  # bottom
                        if c == block.c0:
                            border_count += borders[3]  # left
                        if c == block.c1 - 1:
                            border_count += borders[1]  # right
                        total_edges += 4
            score.border_completeness = border_count / max(total_edges, 1)
        else:
            score.border_completeness = 0.5  # 默认值
        
        # 表头完备性
        if header_rows:
            header_count = len([r for r in header_rows if block.r0 <= r < block.r1])
            score.header_completeness = header_count / max(len(header_rows), 1)
        else:
            score.header_completeness = 0.0
        
        # 综合评分
        score.total = (
            score.density * 0.3 +
            score.type_consistency * 0.25 +
            score.border_completeness * 0.2 +
            score.header_completeness * 0.25
        )
        
        return score
    
    def identify_main_table(self, blocks: List[Block], scores: Dict[str, TableScore]) -> str:
        """
        识别主表（评分最高）
        """
        if not blocks:
            return ""
        
        best_block_id = blocks[0].block_id
        best_score = scores.get(best_block_id, TableScore()).total
        
        for block in blocks[1:]:
            score = scores.get(block.block_id, TableScore()).total
            if score > best_score:
                best_score = score
                best_block_id = block.block_id
        
        return best_block_id
    
    def try_merge_blocks(self, block1: Block, block2: Block, O: np.ndarray, 
                         T: np.ndarray, header_rows: List[int] = None) -> Tuple[bool, float]:
        """
        尝试合并两个块
        返回: (是否合并, 增益值)
        """
        # 计算对齐度
        alignment = self._calculate_alignment(block1, block2)
        
        # 计算类型一致度
        type_consistency = self._calculate_type_consistency(block1, block2, T)
        
        # 计算密度变化
        merged_block = self._merge_bbox(block1, block2)
        merged_region = O[merged_block.r0:merged_block.r1, merged_block.c0:merged_block.c1]
        merged_density = float(np.sum(merged_region)) / max(merged_block.area, 1)
        density_change = merged_density - min(
            float(np.sum(O[block1.r0:block1.r1, block1.c0:block1.c1])) / max(block1.area, 1),
            float(np.sum(O[block2.r0:block2.r1, block2.c0:block2.c1])) / max(block2.area, 1)
        )
        
        # 惩罚（如果块之间距离太远）
        penalty = self._calculate_penalty(block1, block2)
        
        # 增益
        gain = (
            0.4 * alignment +
            0.3 * type_consistency +
            0.2 * max(0, density_change) -
            0.1 * penalty
        )
        
        should_merge = gain >= self.config.merge_gain_threshold
        
        return should_merge, gain
    
    def _calculate_alignment(self, block1: Block, block2: Block) -> float:
        """计算列对齐度"""
        # 如果水平相邻
        if block1.r0 == block2.r0 and block1.r1 == block2.r1:
            # 检查列是否对齐
            if block1.c1 == block2.c0 or block2.c1 == block1.c0:
                return 1.0
        
        # 如果垂直相邻
        if block1.c0 == block2.c0 and block1.c1 == block2.c1:
            if block1.r1 == block2.r0 or block2.r1 == block1.r0:
                return 0.8
        
        return 0.0
    
    def _calculate_type_consistency(self, block1: Block, block2: Block, T: np.ndarray) -> float:
        """计算类型一致度"""
        # 简化：检查重叠列的類型
        overlap_c0 = max(block1.c0, block2.c0)
        overlap_c1 = min(block1.c1, block2.c1)
        
        if overlap_c1 <= overlap_c0:
            return 0.0
        
        consistency = 0.0
        for c in range(overlap_c0, overlap_c1):
            types1 = []
            types2 = []
            for r in range(block1.r0, block1.r1):
                if r < T.shape[0] and c < T.shape[1]:
                    types1.append(T[r, c])
            for r in range(block2.r0, block2.r1):
                if r < T.shape[0] and c < T.shape[1]:
                    types2.append(T[r, c])
            
            if types1 and types2:
                common1 = Counter(types1).most_common(1)[0][0]
                common2 = Counter(types2).most_common(1)[0][0]
                if common1 == common2:
                    consistency += 1.0
        
        return consistency / max(overlap_c1 - overlap_c0, 1)
    
    def _merge_bbox(self, block1: Block, block2: Block) -> Block:
        """合并两个块的边界框"""
        return Block(
            min(block1.r0, block2.r0),
            max(block1.r1, block2.r1),
            min(block1.c0, block2.c0),
            max(block1.c1, block2.c1)
        )
    
    def _calculate_penalty(self, block1: Block, block2: Block) -> float:
        """计算合并惩罚（距离越远惩罚越大）"""
        # 计算块之间的最小距离
        r_gap = max(0, max(block1.r0, block2.r0) - min(block1.r1, block2.r1))
        c_gap = max(0, max(block1.c0, block2.c0) - min(block1.c1, block2.c1))
        gap = max(r_gap, c_gap)
        
        # 归一化惩罚
        return min(1.0, gap / 10.0)
    
    def clean_dataframe(self, df: pd.DataFrame, header_rows: List[int], 
                       unit_patterns: List[str]) -> Tuple[pd.DataFrame, Optional[str], List[int]]:
        """
        清洗 DataFrame
        返回: (清洗后的df, 单位字符串, 移除的行索引列表)
        """
        df_cleaned = df.copy()
        removed_rows = []
        unit_str = None
        
        # 1. 移除中段重复表头
        if self.config.allow_mid_headers:
            removed_rows = self._remove_mid_headers(df_cleaned, header_rows)
        
        # 2. 抽取单位行
        for pattern in unit_patterns:
            unit_str = self._extract_unit_line(df_cleaned, pattern)
            if unit_str:
                break
        
        # 3. 解析日期、金额等（简化实现）
        # 这里可以添加更复杂的解析逻辑
        
        return df_cleaned, unit_str, removed_rows
    
    def _remove_mid_headers(self, df: pd.DataFrame, header_rows: List[int]) -> List[int]:
        """移除中段重复表头"""
        if not header_rows:
            return []
        
        removed = []
        header_pattern = None
        
        # 构建表头模式（简化：检查前几列是否与表头行相似）
        if header_rows:
            first_header_row = header_rows[0]
            if first_header_row < df.shape[0]:
                header_pattern = [str(df.iloc[first_header_row, c]).strip() 
                                 for c in range(min(5, df.shape[1]))]
        
        if not header_pattern:
            return []
        
        # 扫描数据行，查找相似表头
        for r in range(max(header_rows) + 1, df.shape[0]):
            row_pattern = [str(df.iloc[r, c]).strip() 
                          for c in range(min(5, df.shape[1]))]
            
            # 检查相似度
            similarity = sum(1 for h, r in zip(header_pattern, row_pattern) if h == r and h != "")
            if similarity >= len(header_pattern) * 0.7:  # 70% 相似
                removed.append(r)
        
        # 移除这些行
        if removed:
            df.drop(index=df.index[removed], inplace=True)
            df.reset_index(drop=True, inplace=True)
        
        return removed
    
    def _extract_unit_line(self, df: pd.DataFrame, pattern: str) -> Optional[str]:
        """抽取单位行"""
        import re
        regex = re.compile(pattern)
        
        for r in range(min(10, df.shape[0])):  # 只检查前10行
            for c in range(min(5, df.shape[1])):
                val = df.iloc[r, c]
                if pd.notna(val):
                    if regex.match(str(val)):
                        return str(val).strip()
        
        return None

