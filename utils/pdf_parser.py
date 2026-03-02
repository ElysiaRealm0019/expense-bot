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


    # 非交易行过滤模式（用于排除标题、汇总等）
    NON_TRANSACTION_PATTERNS = [
        # 日期范围 "01/12/2025 - 28/02/2026"
        re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}\s*-\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}'),
        # 账户标题 "Personal Account statement", "Personal Account balance"
        re.compile(r'^Personal\s+Account', re.IGNORECASE),
        # 表格列标题
        re.compile(r'^Date\s+Description', re.IGNORECASE),
        re.compile(r'^Description.*\(GBP\)', re.IGNORECASE),
        # 汇总行关键词
        re.compile(r'^(Total outgoings|Total deposits|Balance in Pots|Account number|Sort code|IBAN|BIC|Monzo Bank|Excluding all Pots)', re.IGNORECASE),
        # 纯金额行（没有描述，只有 £ 符号和金额，通常是余额）
        re.compile(r'^£\s*\d{1,3}(,\d{3})*(\.\d{2})?\s*$'),
        # 仅国家代码行 (GBR, CHN 等)
        re.compile(r'^(GBR|CHF|USD|EUR|CNY|JPY|AUD|CAD|HKD|SGD)$'),
        # 空行或只有空白
        re.compile(r'^\s*$'),
    ]

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
        
        策略（针对 Monzo 等多行列格式优化）：
        1. 检测表格标题来定位交易区域
        2. 识别日期行并提取后续行的金额
        3. 过滤非交易行（标题、汇总、日期范围等）
        4. 去重处理（更严格的去重规则）
        """
        transactions = []
        seen_keys = set()  # 用于去重
        
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行
            if not line:
                i += 1
                continue
            
            # 检查是否匹配非交易行模式
            if self._is_non_transaction_line(line):
                i += 1
                continue
            
            # 尝试提取日期
            date = self._extract_date(line)
            if not date:
                i += 1
                continue
            
            # 尝试在同一行或后续行中提取金额
            amount = None
            description_parts = [line]
            
            # 在当前行及后续几行寻找金额
            for look_ahead in range(5):
                if i + look_ahead >= len(lines):
                    break
                check_line = lines[i + look_ahead].strip()
                
                if not check_line:
                    continue
                
                # 如果是日期行，继续
                if self._extract_date(check_line) and look_ahead > 0:
                    break
                
                # 跳过非交易行
                if self._is_non_transaction_line(check_line):
                    continue
                
                # 尝试提取金额
                potential_amount = self._extract_amount(check_line)
                if potential_amount is not None:
                    # 过滤太小的金额（可能是余额）
                    if abs(potential_amount) < 0.50 and potential_amount != 0:
                        i += 1
                        continue
                    
                    amount = potential_amount
                    # 收集金额前的所有行作为描述
                    for j in range(look_ahead):
                        desc_line = lines[i + j].strip()
                        if desc_line and not self._extract_date(desc_line):
                            description_parts.append(desc_line)
                    i += look_ahead
                    break
            
            if amount is None:
                i += 1
                continue
            
            # 构建描述
            desc = ' '.join([p for p in description_parts if p])
            for pattern, _ in self.DATE_PATTERNS:
                desc = pattern.sub('', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()
            
            amount_clean_pattern = re.compile(r'[-–—]?\s*(?:£|\$|€|¥)?\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?:\s*CR|\s*DR)?')
            desc = amount_clean_pattern.sub('', desc)
            desc = desc.strip()
            
            if len(desc) < 2:
                i += 1
                continue
            
            # 判断类型
            tx_type = self._detect_type(amount, desc)
            
            # 标准化金额
            abs_amount = abs(amount)
            
            # 严格的去重检查 - 基于日期和金额
            # 金额相近（相差小于0.01）且日期相同的视为重复
            found_duplicate = False
            date_str = date.strftime('%Y-%m-%d')
            for existing in transactions:
                existing_date_str = existing.date.strftime('%Y-%m-%d')
                if existing_date_str == date_str and abs(existing.amount - abs_amount) < 0.01:
                    # 如果已有交易，跳过这个
                    found_duplicate = True
                    break
            
            if found_duplicate:
                i += 1
                continue
            
            # 分类
            category = self._match_category(desc, tx_type)
            
            transactions.append(ParsedTransaction(
                date=date,
                amount=abs_amount,
                description=desc,
                type=tx_type,
                category=category
            ))
            
            i += 1
        
        return transactions
    
    def _is_non_transaction_line(self, line: str) -> bool:
        """检查是否是非交易行（标题、汇总、日期范围等）"""
        line = line.strip()
        if not line:
            return True
        
        for pattern in self.NON_TRANSACTION_PATTERNS:
            if pattern.match(line):
                return True
        
        # 检查是否包含非交易关键词
        line_lower = line.lower()
        for keyword in ['balance', 'total outgoings', 'total deposits', 'statement', 
                       'account number', 'sort code', 'iban', 'bic', 'registered']:
            if keyword in line_lower and not self._extract_date(line):
                return True
        
        return False

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
        """从文本中提取金额（更严格的策略）"""
        text = text.strip()
        if not text:
            return None
            
        text_upper = text.upper()
        
        # 检查是否有明确的负号在金额前面
        has_explicit_negative = text.startswith('-') or text.startswith('–') or text.startswith('—')
        
        # 策略1：优先匹配带货币符号的金额（最可靠）
        # 匹配格式：£1,234.56, -50.00, $100.50, €100 等
        currency_amount_pattern = re.compile(
            r'^'  # 从行首开始
            r'(?:[-–—]\s*)?'  # 可选负号
            r'(£|\$|€|¥)'  # 必须有货币符号
            r'\s*'  # 可选空格
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'  # 主金额
            r'(?:\s*CR|\s*DR)?'  # 可选 CR/DR 后缀
            r'$'
        )
        
        match = currency_amount_pattern.match(text)
        if match:
            sign = -1 if (has_explicit_negative or 'DR' in text_upper) else 1
            try:
                val = float(match.group(2).replace(',', ''))
                return sign * val
            except ValueError:
                pass
        
        # 策略2：纯金额行（只有金额，没有其他文字）
        # 匹配格式：-30.00, 100.50, 1,234.56 等
        # 排除看起来像日期的数字（如 20/02/2026 里的 2026）
        pure_amount_pattern = re.compile(
            r'^'  # 从行首开始
            r'(?:[-–—]\s*)?'  # 可选负号
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2}))'  # 金额（必须2位小数）
            r'$'
        )
        
        # 检查行是否像纯金额（没有字母，除了CR/DR）
        if pure_amount_pattern.match(text) and not re.search(r'[A-Za-z]', text.replace('CR', '').replace('DR', '')):
            has_dr = 'DR' in text_upper
            has_cr = 'CR' in text_upper
            sign = -1 if (has_explicit_negative or has_dr) else (1 if has_cr else 1)
            try:
                val = float(text.replace(',', '').replace('-', '').replace('–', '').replace('—', '').strip())
                # 排除年份大小的数字 (1900-2100 范围可能是年份)
                if 1900 <= val <= 2100 and '.' not in text:
                    return None
                return sign * val
            except ValueError:
                pass
        
        # 策略3：行尾的金额（有货币符号或明确的金额特征）
        # 需要更严格的判断
        trailing_amount_pattern = re.compile(
            r'(?:[-–—]\s*)?'  # 可选负号
            r'(?:£|\$|€|¥)?\s*'  # 可选货币符号
            r'(\d{1,3}(?:,\d{3})*\.\d{2})'  # 金额（必须2位小数）
            r'(?:\s*CR|\s*DR)?'  # 可选 CR/DR
            r'$'
        )
        
        # 只有当行看起来像交易金额时才使用策略3
        # 交易金额行通常：有负号，或有两位小数，或有货币符号
        if re.search(r'[.-].*\.\d{2}', text) or re.search(r'^[£$€¥]', text):
            match = trailing_amount_pattern.search(text)
            if match:
                sign = -1 if (has_explicit_negative or 'DR' in text_upper) else (1 if 'CR' in text_upper else 1)
                try:
                    val = float(match.group(1).replace(',', ''))
                    # 排除年份大小的数字
                    if 1900 <= val <= 2100:
                        return None
                    return sign * val
                except ValueError:
                    pass
        
        return None

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
