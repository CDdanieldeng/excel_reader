"""
快速测试 - 验证导入是否正常
"""
try:
    from excel_reader import parse_file, ParserConfig
    print("✅ 导入成功！")
    print(f"parse_file 函数: {parse_file}")
    print(f"ParserConfig 类: {ParserConfig}")
    print("\n可以开始使用 parse_file() 函数了！")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()

