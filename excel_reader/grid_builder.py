"""
网格构建器 - 构建占用矩阵、边框图、样式图
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Set, Any
from .models import FileFormat


class GridBuilder:
    """构建网格信号"""
    
    def __init__(self, df: pd.DataFrame, metadata: Dict[str, Any], format: FileFormat):
        self.df = df
        self.metadata = metadata
        self.format = format
        self.n_rows, self.n_cols = df.shape
        
    def build_occupancy_matrix(self) -> np.ndarray:
        """
        构建占用矩阵 O[r, c]: 非空单元为 1
        """
        O = np.zeros((self.n_rows, self.n_cols), dtype=np.int8)
        
        for r in range(self.n_rows):
            for c in range(self.n_cols):
                val = self.df.iloc[r, c]
                # 检查是否非空（排除 None, NaN, 空字符串）
                if pd.notna(val) and str(val).strip() != "":
                    O[r, c] = 1
        
        # 处理隐藏行列
        hidden_rows = self.metadata.get("hidden_rows", set())
        hidden_cols = self.metadata.get("hidden_cols", set())
        
        for r in hidden_rows:
            if 0 <= r < self.n_rows:
                O[r, :] = 0
        
        for c in hidden_cols:
            if 0 <= c < self.n_cols:
                O[:, c] = 0
        
        return O
    
    def build_border_matrix(self) -> np.ndarray:
        """
        构建边框矩阵 B[r, c]: 每个位置记录是否有上下左右边框
        返回形状: (n_rows, n_cols, 4) - [top, right, bottom, left]
        """
        B = np.zeros((self.n_rows, self.n_cols, 4), dtype=np.int8)
        borders = self.metadata.get("borders", {})
        
        for (r, c), border_info in borders.items():
            if 0 <= r < self.n_rows and 0 <= c < self.n_cols:
                if border_info.get("top"):
                    B[r, c, 0] = 1
                if border_info.get("right"):
                    B[r, c, 1] = 1
                if border_info.get("bottom"):
                    B[r, c, 2] = 1
                if border_info.get("left"):
                    B[r, c, 3] = 1
        
        return B
    
    def build_style_matrix(self) -> np.ndarray:
        """
        构建样式矩阵 S[r, c]: 记录样式强度（加粗、背景色等）
        返回标量值，值越大表示样式越强（可能是表头）
        """
        S = np.zeros((self.n_rows, self.n_cols), dtype=np.float32)
        styles = self.metadata.get("styles", {})
        
        for (r, c), style_info in styles.items():
            if 0 <= r < self.n_rows and 0 <= c < self.n_cols:
                score = 0.0
                if style_info.get("bold"):
                    score += 0.5
                if style_info.get("bg_color"):
                    score += 0.3
                S[r, c] = score
        
        # 对于 xlsb/csv，样式信息较少，可以基于文本特征推断
        if self.format in (FileFormat.xlsb, FileFormat.csv):
            # 基于文本比例：如果某行文本比例高，可能是表头
            for r in range(min(10, self.n_rows)):  # 只检查前10行
                text_ratio = 0.0
                for c in range(self.n_cols):
                    val = self.df.iloc[r, c]
                    if pd.notna(val):
                        sval = str(val).strip()
                        # 检查是否为文本（非数字、非日期）
                        if sval and not self._is_numeric(sval):
                            text_ratio += 1.0
                text_ratio /= max(self.n_cols, 1)
                S[r, :] += text_ratio * 0.2  # 降权
        
        return S
    
    def build_type_matrix(self) -> np.ndarray:
        """
        构建类型矩阵 T[r, c]: 记录单元格类型（文本/数字/日期等）
        返回: 0=空, 1=文本, 2=数字, 3=日期
        """
        T = np.zeros((self.n_rows, self.n_cols), dtype=np.int8)
        
        for r in range(self.n_rows):
            for c in range(self.n_cols):
                val = self.df.iloc[r, c]
                if pd.isna(val) or str(val).strip() == "":
                    T[r, c] = 0
                elif self._is_numeric(str(val)):
                    T[r, c] = 2
                elif self._is_date_like(str(val)):
                    T[r, c] = 3
                else:
                    T[r, c] = 1
        
        return T
    
    def get_merged_cells(self) -> list:
        """获取合并单元格信息"""
        return self.metadata.get("merged_cells", [])
    
    def _is_numeric(self, s: str) -> bool:
        """判断字符串是否为数字"""
        try:
            float(s.replace(",", "").replace("%", "").replace("¥", "").replace("$", ""))
            return True
        except:
            return False
    
    def _is_date_like(self, s: str) -> bool:
        """判断字符串是否像日期"""
        date_indicators = ["-", "/", "年", "月", "日", ":", "T"]
        return any(indicator in s for indicator in date_indicators) and len(s) >= 6

