"""
测试示例 - 可以直接运行
"""
import sys
from pathlib import Path
from excel_reader import parse_file, ParserConfig

def test_parse_file():
    """
    测试 parse_file 函数
    使用示例文件或创建测试数据
    """
    print("=" * 60)
    print("Excel Reader 测试示例")
    print("=" * 60)
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        sheet_names = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    else:
        # 默认测试：创建一个简单的 CSV 文件用于测试
        print("\n未提供文件路径，创建测试 CSV 文件...")
        test_csv_path = "test_data.csv"
        create_test_csv(test_csv_path)
        file_path = test_csv_path
        sheet_names = None  # CSV 文件不需要 sheet_name
    
    print(f"\n解析文件: {file_path}")
    print(f"Sheet 名称: {sheet_names}")
    print("-" * 60)
    
    try:
        # 调用主函数
        dfs, metas = parse_file(
            file_path=file_path,
            sheet_name=sheet_names,
            output_dir="outputs",
            export_csv=True,
            config=ParserConfig()
        )
        
        # 显示结果
        print(f"\n✅ 解析成功！共识别到 {len(dfs)} 个表格")
        print("-" * 60)
        
        for key, df in dfs.items():
            meta = metas[key]
            print(f"\n{key}:")
            print(f"  形状: {df.shape} (行 x 列)")
            print(f"  列名: {list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}")
            print(f"  是否主表: {meta.is_main}")
            print(f"  综合评分: {meta.score.total:.3f}")
            print(f"  密度: {meta.score.density:.3f}")
            print(f"  CSV路径: {meta.csv_path}")
            print(f"\n  前3行数据:")
            print(df.head(3).to_string())
            print()
        
        print("=" * 60)
        print("✅ 测试完成！输出文件已保存到 outputs/ 目录")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def create_test_csv(file_path: str):
    """创建一个简单的测试 CSV 文件"""
    import csv
    
    data = [
        ["日期", "产品", "收入", "成本", "毛利率"],
        ["2024-01-01", "产品A", "1000", "600", "40%"],
        ["2024-01-02", "产品B", "2000", "1200", "40%"],
        ["2024-01-03", "产品A", "1500", "900", "40%"],
        ["2024-01-04", "产品C", "3000", "1800", "40%"],
        ["2024-01-05", "产品B", "2500", "1500", "40%"],
    ]
    
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(data)
    
    print(f"✅ 已创建测试文件: {file_path}")


if __name__ == "__main__":
    # 运行测试
    test_parse_file()

