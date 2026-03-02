#!/usr/bin/env python3
"""
PDF 解析测试脚本

用于测试 PDF 银行账单解析功能。
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.pdf_parser import PDFParser, ParsedTransaction
from datetime import datetime


def test_date_extraction():
    """测试日期提取"""
    parser = PDFParser()
    
    test_cases = [
        ("01/01/2024", datetime(2024, 1, 1)),
        ("31/12/2023", datetime(2023, 12, 31)),
        ("2024-06-15", datetime(2024, 6, 15)),
        ("15.06.2024", datetime(2024, 6, 15)),
        ("01 Jan 2024", datetime(2024, 1, 1)),
    ]
    
    print("🗓️  日期提取测试:")
    for date_str, expected in test_cases:
        result = parser._extract_date(date_str)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{date_str}' -> {result}")
    
    print()


def test_amount_extraction():
    """测试金额提取"""
    parser = PDFParser()
    
    test_cases = [
        ("£1,234.56", 1234.56),
        ("-50.00", -50.00),
        ("100.50 CR", 100.50),
        ("£250", 250.0),
        ("- £75.25", -75.25),
    ]
    
    print("💷 金额提取测试:")
    for text, expected in test_cases:
        result = parser._extract_amount(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{text}' -> {result} (expected: {expected})")
    
    print()


def test_type_detection():
    """测试类型检测"""
    parser = PDFParser()
    
    test_cases = [
        (100.0, "salary payment", "income"),
        (-50.0, "coffee shop", "expense"),
        (50.0, "amazon purchase", "expense"),
        (2000.0, "monthly salary", "income"),
    ]
    
    print("🏷️  类型检测测试:")
    for amount, desc, expected in test_cases:
        result = parser._detect_type(amount, desc)
        status = "✅" if result == expected else "❌"
        print(f"  {status} amount={amount}, desc='{desc}' -> {result} (expected: {expected})")
    
    print()


def test_category_matching():
    """测试分类匹配"""
    parser = PDFParser()
    
    test_cases = [
        ("STARBUCKS COFFEE", "expense", "餐饮"),
        ("UBER TRIP", "expense", "交通"),
        ("TESCO SUPERMARKET", "expense", "购物"),
        ("NETFLIX SUBSCRIPTION", "expense", "娱乐"),
        ("MONTHLY SALARY", "income", "工资"),
        ("unknown merchant", "expense", None),
    ]
    
    print("📂 分类匹配测试:")
    for desc, tx_type, expected in test_cases:
        result = parser._match_category(desc, tx_type)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{desc}' -> {result} (expected: {expected})")
    
    print()


def test_line_parsing():
    """测试行解析"""
    parser = PDFParser()
    
    test_lines = [
        "01/01/2024  STARBUCKS COFFEE  £4.50",
        "15/06/2024  UBER TRIP  -£15.00",
        "2024-06-20  MONTHLY SALARY  £2500.00",
        "31/12/2023  AMAZON PURCHASE  £35.99",
    ]
    
    print("📝 行解析测试:")
    for line in test_lines:
        result = parser._parse_line(line)
        if result:
            date, amount, desc = result
            print(f"  ✅ '{line[:40]}...'")
            print(f"      -> date={date}, amount={amount}, desc='{desc[:30]}...'")
        else:
            print(f"  ❌ '{line}' -> Failed to parse")
    print()


def main():
    """运行所有测试"""
    print("=" * 50)
    print("🧪 PDF 解析器测试")
    print("=" * 50)
    print()
    
    test_date_extraction()
    test_amount_extraction()
    test_type_detection()
    test_category_matching()
    test_line_parsing()
    
    print("=" * 50)
    print("✅ 所有测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
