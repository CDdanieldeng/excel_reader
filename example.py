"""
使用示例
"""
from excel_reader import parse_file, ParserConfig

# 示例 1: 解析 Excel 文件
def example_xlsx():
    dfs, metas = parse_file(
        file_path="inputs/本月报表.xlsx",
        sheet_name=["财务数据", "销售表"],
        output_dir="outputs",
        export_csv=True,
        config=ParserConfig()
    )
    
    # 访问解析后的数据
    for key, df in dfs.items():
        print(f"\n{key}:")
        print(f"  形状: {df.shape}")
        print(f"  列名: {df.columns.tolist()}")
        print(f"  前5行:")
        print(df.head())
        
        # 访问元数据
        meta = metas[key]
        print(f"  是否主表: {meta.is_main}")
        print(f"  评分: {meta.score.total:.2f}")
        print(f"  CSV路径: {meta.csv_path}")


# 示例 2: 解析 CSV 文件
def example_csv():
    dfs, metas = parse_file(
        file_path="inputs/data.csv",
        sheet_name=None,  # CSV 文件必须为 None
        output_dir="outputs",
        export_csv=True
    )
    
    for key, df in dfs.items():
        print(f"\n{key}: {df.shape}")


# 示例 3: 自定义配置
def example_custom_config():
    config = ParserConfig(
        min_block_height=5,
        min_block_width=4,
        density_threshold=0.4,
        max_header_rows=8,
        keep_leaf_only=True,
    )
    
    dfs, metas = parse_file(
        file_path="inputs/complex_table.xlsx",
        sheet_name=["Sheet1"],
        config=config
    )


if __name__ == "__main__":
    print("Excel Reader 使用示例")
    print("=" * 50)
    
    # 运行示例（需要实际文件）
    # example_xlsx()
    # example_csv()
    # example_custom_config()
    
    print("\n请将示例文件路径替换为实际文件路径后运行")

