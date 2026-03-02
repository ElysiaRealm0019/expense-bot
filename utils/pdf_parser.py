"""
PDF 银行账单解析模块

使用 PyMuPDF 解析银行 PDF 账单，提取交易记录。
支持多种银行账单格式，通过正则表达式识别日期和金额。

功能：
- PDF 文本提取
- 交易日期识别（支持多种格式）
- 交易金额识别（支持正负金额）
- 自动检测交易类型（收入/支出）
- 分类自动匹配

作者：SE.AR.PH
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class ParsedTransaction:
    """解析后的交易记录"""
    date: datetime
    amount: float
    description: str
    type: str  # "income" or "expense"
    category: Optional[str] = None
    confidence: float = 1.0  # 匹配置信度


class PDFParser:
    """PDF 银行账单解析器"""

    # 日期格式模式（按优先级排序）
    DATE_PATTERNS = [
        # DD/MM/YYYY
        (re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})'), '%d/%m/%Y'),
        # DD-MM-YYYY
        (re.compile(r'(\d{1,2})-(\d{1,2})-(\d{4})'), '%d-%m-%Y'),
        # DD.MM.YYYY
        (re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})'), '%d.%m.%Y'),
        # YYYY-MM-DD
        (re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})'), '%Y-%m-%d'),
        # DD MMM YYYY (e.g., 01 Jan 2024)
        (re.compile(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', re.IGNORECASE), '%d %b %Y'),
        # MMM DD, YYYY (e.g., Jan 01, 2024)
        (re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})', re.IGNORECASE), '%b %d, %Y'),
    ]

    # 金额模式
    # 匹配带逗号的千分位，以及可能的货币符号
    AMOUNT_PATTERN = re.compile(
        r'(?:£|\$|€|¥|GBP|USD|EUR)?\s*'  # 货币符号（可选）
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'  # 主金额（支持千分位）
        r'(?:\s*CR|\s*DR)?'  # CR/DR 后缀
        r'(?:\s*\((\d+)\))?'  # 括号中的便士/分
    )

    # 负金额标记 - 但要排除收入相关的
    NEGATIVE_INDICATORS = ['-', 'DR', 'debit', 'paid to', 'payment to']
    POSITIVE_INDICATORS = ['+', 'CR', 'credit', 'deposit', 'received', 'refund', 'salary', 'wage', 'pay']

    # 分类关键词映射
    CATEGORY_KEYWORDS = {
        # 餐饮
        "餐饮": ['restaurant', 'cafe', 'coffee', 'starbucks', 'mcdonald', 'kfc', 'burger', 
                 'pizza', 'deliveroo', 'uber eats', 'just eat', 'food', 'dining', 'bar', 'pub',
                 '咖啡', '餐厅', '外卖', '快餐'],
        # 交通
        "交通": ['uber', 'lyft', 'taxi', 'train', 'bus', 'metro', 'tube', 'rail', 'station',
                 'petrol', 'fuel', 'parking', 'car', 'bike', 'taxi', 'airline', 'flight',
                 '打车', '汽油', '停车'],
        # 购物
        "购物": ['amazon', 'ebay', 'shop', 'store', 'market', 'supermarket', 'tesco', 'sainsbury',
                 'asda', 'waitrose', 'morrisons', 'clothes', 'fashion', 'retail', 'gift',
                 '购物', '超市', '商场'],
        # 娱乐
        "娱乐": ['netflix', 'spotify', 'cinema', 'movie', 'theatre', 'concert', 'game', 'gaming',
                 'steam', 'playstation', 'xbox', 'subscription', 'entertainment',
                 '电影', '游戏', '音乐'],
        # 居住
        "居住": ['rent', 'mortgage', 'utility', 'electric', 'gas', 'water', 'internet', 'phone',
                 'broadband', 'council tax', 'insurance', '房租', '水电', '保险'],
        # 医疗
        "医疗": ['pharmacy', 'doctor', 'hospital', 'medical', 'dentist', 'health', 'nhs',
                 '药店', '医生', '医院'],
        # 教育
        "教育": ['school', 'university', 'college', 'course', 'book', 'education', 'tuition',
                 '学校', '大学', '课程', '书'],
        # 工资
        "工资": ['salary', 'wage', 'pay', 'payroll', 'employer', 'monthly salary', '工资', '薪资'],
        # 奖金
        "奖金": ['bonus', 'commission', 'overtime', '奖金', '佣金'],
        # 投资
        "投资": ['investment', 'dividend', 'interest', 'stock', 'share', 'fund', 'ETF', 'crypto',
                 '投资', '股息', '股票'],
    }

    def __init__(self, categories: Optional[List[Dict]] = None):
        """
        初始化解析器
        
        Args:
            categories: 可选的分类列表，用于自动匹配
        """
        self.categories = categories or []
        self._build_category_lookup()

    def _build_category_lookup(self):
        """构建分类快速查找表"""
        self.category_lookup = {}
        if self.categories:
            for cat in self.categories:
                name = cat.get('name', '').lower()
                cat_type = cat.get('type', '')
                self.category_lookup[name] = {
                    'id': cat.get('id'),
                    'name': cat.get('name'),
                    'type': cat_type
                }

    def parse_pdf(self, pdf_path: str) -> List[ParsedTransaction]:
        """
        解析 PDF 文件
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            解析后的交易列表
        """
        transactions = []
        
        try:
            doc = fitz.open(pdf_path)
            logger.info(f"PDF opened: {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                page_transactions = self._extract_transactions(text)
                transactions.extend(page_transactions)
                logger.debug(f"Page {page_num + 1}: extracted {len(page_transactions)} transactions")
            
            doc.close()
            
            # 按日期排序
            transactions.sort(key=lambda x: x.date)
            
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise
        
        return transactions

    def parse_pdf_bytes(self, pdf_bytes: bytes) -> List[ParsedTransaction]:
        """
        从字节数据解析 PDF
        
        Args:
            pdf_bytes: PDF 文件的字节数据
            
        Returns:
            解析后的交易列表
        """
        transactions = []
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            logger.info(f"PDF opened from bytes: {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                page_transactions = self._extract_transactions(text)
                transactions.extend(page_transactions)
            
            doc.close()
            
            # 按日期排序
            transactions.sort(key=lambda x: x.date)
            
        except Exception as e:
            logger.error(f"Failed to parse PDF from bytes: {e}")
            raise
        
        return transactions

    def _extract_transactions(self, text: str) -> List[ParsedTransaction]:
        """
        从文本中提取交易记录
        
        策略：
        1. 按行分割文本
        2. 每行尝试匹配日期和金额
        3. 根据金额符号和关键词判断类型
        4. 自动匹配分类
        """
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # 尝试提取日期和金额
            result = self._parse_line(line)
            if result:
                date, amount, desc = result
                
                # 判断类型
                tx_type = self._detect_type(amount, desc)
                
                # 标准化金额（取绝对值用于存储）
                abs_amount = abs(amount)
                
                # 自动匹配分类
                category = self._match_category(desc, tx_type)
                
                transactions.append(ParsedTransaction(
                    date=date,
                    amount=abs_amount,
                    description=desc,
                    type=tx_type,
                    category=category
                ))
        
        return transactions

    def _parse_line(self, line: str) -> Optional[Tuple[datetime, float, str]]:
        """
        解析单行文本，提取日期、金额和描述
        
        Returns:
            (date, amount, description) 或 None
        """
        # 提取日期
        date = self._extract_date(line)
        if not date:
            return None
        
        # 提取金额
        amount = self._extract_amount(line)
        if amount is None:
            return None
        
        # 提取描述（去除日期和金额后的部分）
        desc = self._extract_description(line, date, amount)
        
        return date, amount, desc

    def _extract_date(self, text: str) -> Optional[datetime]:
        """从文本中提取日期"""
        for pattern, date_format in self.DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    # 根据格式构建日期字符串
                    if '%d %b' in date_format or '%b %d' in date_format:
                        # 处理月份缩写
                        date_str = match.group(0)
                        return datetime.strptime(date_str, date_format)
                    else:
                        # 直接用格式解析
                        return datetime.strptime(match.group(0), date_format)
                except ValueError:
                    continue
        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        """从文本中提取金额"""
        # 改进的金额提取策略：
        # 1. 首先检查是否有明确的负号标记
        # 2. 然后找金额模式
        
        text_upper = text.upper()
        is_negative = any(marker in text for marker in ['-', '–', '—']) or 'DR' in text_upper
        
        # 更精确的金额正则：支持 £$€¥ 货币符号，支持千分位，支持小数点
        # 匹配格式：£1,234.56, -50.00, 100.50, 100 CR 等
        amount_pattern = re.compile(
            r'(?:[-–—]\s*)?'  # 可选负号
            r'(?:£|\$|€|¥)\s*'  # 可选货币符号（后面可能有空格）
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'  # 主金额
            r'(?:\s*CR|\s*DR)?'  # 可选 CR/DR 后缀
        )
        
        # 备选：没有货币符号的金额
        simple_amount_pattern = re.compile(
            r'(?:[-–—]\s*)?'  # 可选负号
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'  # 主金额
            r'(?:\s*CR|\s*DR)?'  # 可选 CR/DR 后缀
        )
        
        amounts = []
        
        # 先尝试带货币符号的模式
        matches = amount_pattern.findall(text)
        for match in matches:
            try:
                val = float(match.replace(',', ''))
                amounts.append(val)
            except ValueError:
                continue
        
        # 如果没有匹配到，尝试简单模式
        if not amounts:
            matches = simple_amount_pattern.findall(text)
            for match in matches:
                try:
                    val = float(match.replace(',', ''))
                    amounts.append(val)
                except ValueError:
                    continue
        
        if not amounts:
            return None
        
        # 返回最大的金额
        amount = max(amounts)
        
        # 如果有负号标记或 DR，取负值
        if is_negative or 'DR' in text_upper:
            amount = -abs(amount)
        # 如果有 CR 标记，保持正数
        elif 'CR' in text_upper:
            amount = abs(amount)
        
        return amount

    def _extract_description(self, line: str, date: datetime, amount: float) -> str:
        """提取交易描述"""
        # 移除日期和金额后剩余的部分作为描述
        desc = line
        
        # 移除日期
        for pattern, _ in self.DATE_PATTERNS:
            desc = pattern.sub('', desc)
        
        # 移除金额
        amount_patterns = [
            r'[-–—]?\s*(?:£|\$|€|¥)?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?:\s*CR|\s*DR)?',
            r'(?:£|\$|€|¥)?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*CR',
        ]
        for pattern in amount_patterns:
            desc = re.sub(pattern, '', desc)
        
        # 清理
        desc = re.sub(r'\s+', ' ', desc).strip()
        
        # 如果描述为空或太短，使用原始行
        if len(desc) < 2:
            desc = line[:100]  # 取前100字符
        
        return desc

    def _detect_type(self, amount: float, description: str) -> str:
        """检测交易类型（收入/支出）"""
        desc_lower = description.lower()
        
        # 首先通过金额正负判断（最可靠）
        if amount < 0:
            return "expense"
        
        # 通过明确的收入关键词判断
        for keyword in self.POSITIVE_INDICATORS:
            if keyword.lower() in desc_lower:
                return "income"
        
        # 通过明确的支出关键词判断
        for keyword in self.NEGATIVE_INDICATORS:
            if keyword.lower() in desc_lower:
                return "expense"
        
        # 通过金额大小和常见收入词汇判断
        # 大额数字可能是工资/收入
        if amount >= 1000:
            # 检查是否包含工资相关词汇
            if any(kw in desc_lower for kw in ['salary', 'wage', 'pay', 'deposit', 'transfer in']):
                return "income"
        
        # 默认返回支出（更常见）
        return "expense"

    def _match_category(self, description: str, tx_type: str) -> Optional[str]:
        """根据描述匹配分类"""
        desc_lower = description.lower()
        
        # 遍历分类关键词
        for category_name, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in desc_lower:
                    logger.debug(f"Matched category '{category_name}' for '{description}'")
                    return category_name
        
        # 如果有数据库分类，也尝试匹配
        if self.category_lookup:
            for cat_name, cat_info in self.category_lookup.items():
                if cat_name in desc_lower:
                    return cat_info['name']
        
        return None

    def set_categories(self, categories: List[Dict]):
        """设置分类列表"""
        self.categories = categories
        self._build_category_lookup()


def parse_pdf_statement(pdf_path: str, categories: Optional[List[Dict]] = None) -> List[ParsedTransaction]:
    """
    便捷函数：解析 PDF 银行账单
    
    Args:
        pdf_path: PDF 文件路径
        categories: 可选的分类列表
        
    Returns:
        交易记录列表
    """
    parser = PDFParser(categories)
    return parser.parse_pdf(pdf_path)


def parse_pdf_from_bytes(pdf_bytes: bytes, categories: Optional[List[Dict]] = None) -> List[ParsedTransaction]:
    """
    便捷函数：从字节数据解析 PDF
    
    Args:
        pdf_bytes: PDF 文件的字节数据
        categories: 可选的分类列表
        
    Returns:
        交易记录列表
    """
    parser = PDFParser(categories)
    return parser.parse_pdf_bytes(pdf_bytes)
