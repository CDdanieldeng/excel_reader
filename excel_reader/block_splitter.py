"""
表块分割器 - 基于连通域和MDL代价函数
"""
import numpy as np
from collections import deque
from typing import List, Tuple, Dict, Set
from .config import ParserConfig
from .models import FileFormat


class Block:
    """表块"""
    def __init__(self, r0: int, r1: int, c0: int, c1: int, block_id: str = ""):
        self.r0 = r0
        self.r1 = r1
        self.c0 = c0
        self.c1 = c1
        self.block_id = block_id
    
    @property
    def height(self) -> int:
        return self.r1 - self.r0
    
    @property
    def width(self) -> int:
        return self.c1 - self.c0
    
    @property
    def area(self) -> int:
        return self.height * self.width
    
    def __repr__(self):
        return f"Block({self.block_id}: [{self.r0}:{self.r1}, {self.c0}:{self.c1}])"


class BlockSplitter:
    """表块分割器"""
    
    def __init__(self, config: ParserConfig, format: FileFormat):
        self.config = config
        self.format = format
    
    def split_blocks(self, O: np.ndarray, B: np.ndarray = None) -> List[Block]:
        """
        分割表块
        O: 占用矩阵
        B: 边框矩阵（可选，xlsx 使用）
        """
        if O.size == 0:
            return []
        
        # 1. 连通域检测
        blocks = self._connected_components(O)
        
        # 2. 过滤小块
        blocks = [b for b in blocks if b.height >= self.config.min_block_height 
                  and b.width >= self.config.min_block_width]
        
        # 3. 对于 xlsx，使用边框增强
        if self.format == FileFormat.xlsx and B is not None:
            blocks = self._enhance_with_borders(blocks, O, B)
        
        # 4. MDL 决策：判断是否需要进一步拆分
        final_blocks = []
        for block in blocks:
            sub_blocks = self._mdl_split_decision(block, O, B)
            final_blocks.extend(sub_blocks)
        
        # 5. 分配 block_id
        for idx, block in enumerate(final_blocks):
            block.block_id = f"b{idx + 1}"
        
        return final_blocks
    
    def _connected_components(self, O: np.ndarray) -> List[Block]:
        """
        连通域检测，容忍空洞
        """
        n_rows, n_cols = O.shape
        visited = np.zeros_like(O, dtype=bool)
        blocks = []
        
        for r in range(n_rows):
            for c in range(n_cols):
                if O[r, c] == 1 and not visited[r, c]:
                    # 从 (r, c) 开始 BFS
                    block = self._bfs_connected(O, visited, r, c)
                    if block:
                        blocks.append(block)
        
        return blocks
    
    def _bfs_connected(self, O: np.ndarray, visited: np.ndarray, start_r: int, start_c: int) -> Block:
        """
        BFS 连通域，容忍空洞
        """
        n_rows, n_cols = O.shape
        queue = deque([(start_r, start_c)])
        visited[start_r, start_c] = True
        
        min_r, max_r = start_r, start_r
        min_c, max_c = start_c, start_c
        
        while queue:
            r, c = queue.popleft()
            min_r = min(min_r, r)
            max_r = max(max_r, r)
            min_c = min(min_c, c)
            max_c = max(max_c, c)
            
            # 检查邻接（上下左右 + 容忍空洞）
            for dr in range(-self.config.hole_tolerance_rows - 1, self.config.hole_tolerance_rows + 2):
                for dc in range(-self.config.hole_tolerance_cols - 1, self.config.hole_tolerance_cols + 2):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n_rows and 0 <= nc < n_cols:
                        if not visited[nr, nc] and O[nr, nc] == 1:
                            visited[nr, nc] = True
                            queue.append((nr, nc))
        
        # 扩展边界以包含空洞
        r0 = max(0, min_r - self.config.hole_tolerance_rows)
        r1 = min(n_rows, max_r + self.config.hole_tolerance_rows + 1)
        c0 = max(0, min_c - self.config.hole_tolerance_cols)
        c1 = min(n_cols, max_c + self.config.hole_tolerance_cols + 1)
        
        return Block(r0, r1, c0, c1)
    
    def _enhance_with_borders(self, blocks: List[Block], O: np.ndarray, B: np.ndarray) -> List[Block]:
        """
        使用边框信息增强块分割（xlsx）
        基于边框闭合检测轮廓
        """
        # 简化实现：检查边框完整性
        enhanced = []
        for block in blocks:
            # 检查块边界是否有完整边框
            border_score = self._calculate_border_completeness(block, B)
            if border_score > 0.3:  # 有边框则保留
                enhanced.append(block)
            else:
                # 尝试基于边框重新分割
                sub_blocks = self._split_by_border_contours(block, O, B)
                enhanced.extend(sub_blocks)
        
        return enhanced if enhanced else blocks
    
    def _calculate_border_completeness(self, block: Block, B: np.ndarray) -> float:
        """计算边框完整性"""
        if B is None or B.size == 0:
            return 0.0
        
        border_count = 0
        total_count = 0
        
        # 检查边界
        for r in range(block.r0, block.r1):
            for c in range(block.c0, block.c1):
                if r < B.shape[0] and c < B.shape[1]:
                    borders = B[r, c]
                    if r == block.r0:  # 上边界
                        border_count += borders[0]  # top
                    if r == block.r1 - 1:  # 下边界
                        border_count += borders[2]  # bottom
                    if c == block.c0:  # 左边界
                        border_count += borders[3]  # left
                    if c == block.c1 - 1:  # 右边界
                        border_count += borders[1]  # right
                    total_count += 4
        
        return border_count / max(total_count, 1)
    
    def _split_by_border_contours(self, block: Block, O: np.ndarray, B: np.ndarray) -> List[Block]:
        """基于边框轮廓分割（简化实现）"""
        # 简化：如果边框不完整，尝试按空行/空列分割
        return [block]  # 暂时不实现复杂轮廓检测
    
    def _mdl_split_decision(self, block: Block, O: np.ndarray, B: np.ndarray = None) -> List[Block]:
        """
        MDL 代价函数决策：是否拆分
        Cost = α*(1-密度) + β*(1-矩形度) + γ*(块数量)
        """
        # 计算当前块的密度和矩形度
        block_region = O[block.r0:block.r1, block.c0:block.c1]
        density = float(np.sum(block_region)) / max(block.area, 1)
        rectangularity = self._calculate_rectangularity(block, O)
        
        # 不拆分的代价
        cost_no_split = (
            self.config.mdl_weights[0] * (1 - density) +
            self.config.mdl_weights[1] * (1 - rectangularity) +
            self.config.mdl_weights[2] * 1  # 1个块
        )
        
        # 尝试拆分的代价（简化：按空行/空列拆分）
        cost_split = float('inf')
        split_blocks = [block]
        
        # 如果密度太低或矩形度太低，尝试拆分
        if density < self.config.density_threshold or rectangularity < self.config.rectangularity_threshold:
            split_blocks = self._try_split_by_gaps(block, O)
            if len(split_blocks) > 1:
                # 计算拆分后的总代价
                total_cost = 0.0
                for sub_block in split_blocks:
                    sub_region = O[sub_block.r0:sub_block.r1, sub_block.c0:sub_block.c1]
                    sub_density = float(np.sum(sub_region)) / max(sub_block.area, 1)
                    sub_rect = self._calculate_rectangularity(sub_block, O)
                    total_cost += (
                        self.config.mdl_weights[0] * (1 - sub_density) +
                        self.config.mdl_weights[1] * (1 - sub_rect)
                    )
                total_cost += self.config.mdl_weights[2] * len(split_blocks)
                cost_split = total_cost
        
        # 选择代价更小的方案
        if cost_split < cost_no_split:
            return split_blocks
        else:
            return [block]
    
    def _calculate_rectangularity(self, block: Block, O: np.ndarray) -> float:
        """计算矩形度：实际占用区域与矩形框的比例"""
        block_region = O[block.r0:block.r1, block.c0:block.c1]
        occupied = np.sum(block_region)
        total = block.area
        return float(occupied) / max(total, 1)
    
    def _try_split_by_gaps(self, block: Block, O: np.ndarray) -> List[Block]:
        """尝试按空行/空列拆分"""
        block_region = O[block.r0:block.r1, block.c0:block.c1]
        n_rows, n_cols = block_region.shape
        
        # 查找空行
        empty_rows = []
        for r in range(n_rows):
            if np.sum(block_region[r, :]) == 0:
                empty_rows.append(r)
        
        # 查找空列
        empty_cols = []
        for c in range(n_cols):
            if np.sum(block_region[:, c]) == 0:
                empty_cols.append(c)
        
        # 如果空行/空列足够大，则拆分
        if len(empty_rows) >= 2:
            # 按空行拆分
            splits = []
            start = 0
            for empty_r in empty_rows:
                if empty_r - start >= self.config.min_block_height:
                    splits.append(Block(
                        block.r0 + start,
                        block.r0 + empty_r,
                        block.c0,
                        block.c1
                    ))
                start = empty_r + 1
            if block.r1 - (block.r0 + start) >= self.config.min_block_height:
                splits.append(Block(
                    block.r0 + start,
                    block.r1,
                    block.c0,
                    block.c1
                ))
            if len(splits) > 1:
                return splits
        
        if len(empty_cols) >= 2:
            # 按空列拆分
            splits = []
            start = 0
            for empty_c in empty_cols:
                if empty_c - start >= self.config.min_block_width:
                    splits.append(Block(
                        block.r0,
                        block.r1,
                        block.c0 + start,
                        block.c0 + empty_c
                    ))
                start = empty_c + 1
            if block.c1 - (block.c0 + start) >= self.config.min_block_width:
                splits.append(Block(
                    block.r0,
                    block.r1,
                    block.c0 + start,
                    block.c1
                ))
            if len(splits) > 1:
                return splits
        
        return [block]

