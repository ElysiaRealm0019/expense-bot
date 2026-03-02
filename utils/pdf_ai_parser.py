"""
AI PDF 银行账单解析模块

使用 OpenAI/MiniMax API 解析银行 PDF 账单，提取交易记录。
相比正则表达式，能更好地处理复杂格式和手写/扫描账单。

功能：
- PDF 文本/图像提取
- AI 智能解析交易记录
- 多 API 支持（OpenAI / MiniMax）
- 结构化输出
- 分类自动匹配

作者：SE.AR.PH
"""

import base64
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from io import BytesIO

import fitz  # PyMuPDF
import requests

logger = logging.getLogger(__name__)


class AIAbstractParser:
    """AI 解析器基类"""

    def __init__(
        self,
        categories: Optional[List[Dict]] = None,
        api_key: str = "",
        model: str = "gpt-4o",
    ):
        self.categories = categories or []
        self.api_key = api_key
        self.model = model
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

    def parse(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """解析 PDF（子类实现）"""
        raise NotImplementedError

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        categories_text = "\n".join([
            f"- {cat.get('name', '')} ({cat.get('type', '')})"
            for cat in self.categories
        ]) or "无"

        return f"""你是一个专业的银行账单解析助手。你的任务是从银行 PDF 账单中提取所有交易记录。

## 分类列表（请优先使用这些分类）:
{categories_text}

## 输出格式要求:
请返回 JSON 数组格式，每条交易包含以下字段：
- date: 交易日期（YYYY-MM-DD 格式）
- amount: 交易金额（正数表示收入，负数表示支出）
- description: 交易描述/商户名称
- type: "income" 或 "expense"
- category: 匹配的分类名称（可选）

## 重要规则:
1. 仔细阅读每一行，识别所有交易记录
2. 处理各种日期格式，统一转为 YYYY-MM-DD
3. 处理各种金额格式（带货币符号、千分位、CR/DR 等）
4. 识别交易类型：工资、奖金、股息等为收入；购物、餐饮、交通等为支出
5. 根据描述自动匹配最合适的分类
6. 如果无法确定分类，留空即可
7. 确保返回的是有效 JSON，不要包含任何其他文字
8. 如果没有找到任何交易，返回空数组 []

请开始解析！"""

    def _get_user_prompt(self, content: str) -> str:
        """获取用户提示词"""
        return f"""请解析以下银行账单内容，提取所有交易记录：

{content}

请以 JSON 数组格式返回结果。"""


class OpenAIParser(AIAbstractParser):
    """OpenAI API 解析器"""

    def __init__(
        self,
        categories: Optional[List[Dict]] = None,
        api_key: str = "",
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
    ):
        super().__init__(categories, api_key, model)
        self.base_url = base_url

    def parse(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """使用 OpenAI API 解析 PDF"""
        import requests

        # 将 PDF 转为 base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # 构建请求
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请解析这个银行 PDF 账单，提取所有交易记录。"
                        },
                        {
                            "type": "input_file",
                            "file": {
                                "file_data": f"data:application/pdf;base64,{pdf_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 8192,
            "temperature": 0.1
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']

            # 提取 JSON
            return self._extract_json(content)

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise RuntimeError(f"OpenAI API 请求失败: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            raise RuntimeError(f"解析 API 响应失败: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise RuntimeError(f"JSON 解析失败: {e}")

    def _extract_json(self, content: str) -> List[Dict[str, Any]]:
        """从响应中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从 Markdown 代码块中提取
        match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到 JSON 数组
        match = re.search(r'(\[[\s\S]*)', content)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复截断的 JSON
                fixed = self._extract_partial_json(json_str)
                if fixed:
                    return fixed
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise RuntimeError("无法从响应中提取 JSON 数据")


class MiniMaxParser(AIAbstractParser):
    """MiniMax API 解析器"""

    def __init__(
        self,
        categories: Optional[List[Dict]] = None,
        api_key: str = "",
        model: str = "abab6.5s-chat",
        base_url: str = "https://api.minimax.chat/v1",
    ):
        super().__init__(categories, api_key, model)
        self.base_url = base_url

    def parse(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """使用 MiniMax API 解析 PDF"""
        import requests

        # 将 PDF 转为 base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # 构建请求
        url = f"{self.base_url}/text/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # MiniMax 支持文件上传
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请解析这个银行 PDF 账单，提取所有交易记录。"
                        },
                        {
                            "type": "file",
                            "file": {
                                "type": "pdf",
                                "pdf": {
                                    "file_data": f"data:application/pdf;base64,{pdf_base64}"
                                }
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 8192,
            "temperature": 0.1
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']

            # 提取 JSON
            return self._extract_json(content)

        except requests.exceptions.RequestException as e:
            logger.error(f"MiniMax API request failed: {e}")
            raise RuntimeError(f"MiniMax API 请求失败: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse MiniMax response: {e}")
            raise RuntimeError(f"解析 API 响应失败: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise RuntimeError(f"JSON 解析失败: {e}")

    def _extract_json(self, content: str) -> List[Dict[str, Any]]:
        """从响应中提取 JSON"""
        # 与 OpenAI 相同的提取逻辑
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r'(\[[\s\S]*)', content)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复截断的 JSON
                fixed = self._extract_partial_json(json_str)
                if fixed:
                    return fixed
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise RuntimeError("无法从响应中提取 JSON 数据")


# ========== PDF 分块处理函数 ==========

def split_pdf_by_pages(pdf_bytes: bytes, pages_per_chunk: int = 3) -> List[bytes]:
    """
    将 PDF 按页数分割成多个块
    
    Args:
        pdf_bytes: PDF 文件字节数据
        pages_per_chunk: 每块包含的页数（默认 3 页）
        
    Returns:
        PDF 块列表（每个元素是一个 PDF 的字节数据）
    """
    chunks = []
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        
        for start in range(0, total_pages, pages_per_chunk):
            end = min(start + pages_per_chunk, total_pages)
            chunk_doc = fitz.open()
            for page_num in range(start, end):
                chunk_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            chunks.append(chunk_doc.tobytes())
            chunk_doc.close()
        
        doc.close()
        logger.info(f"Split PDF into {len(chunks)} chunks ({pages_per_chunk} pages each)")
        
    except Exception as e:
        logger.error(f"Failed to split PDF: {e}")
        raise RuntimeError(f"PDF 分块失败: {e}")
    
    return chunks


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """
    获取 PDF 页数
    
    Args:
        pdf_bytes: PDF 文件字节数据
        
    Returns:
        PDF 页数
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get PDF page count: {e}")
        return 0


def merge_transaction_results(results: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    合并多个 PDF 块的解析结果
    
    处理步骤：
    1. 合并所有交易
    2. 按日期和金额去重
    3. 按日期排序
    
    Args:
        results: 解析结果列表（每个元素是一个块的交易列表）
        
    Returns:
        合并去重后的交易列表
    """
    all_transactions = []
    
    # 1. 合并所有交易
    for chunk_result in results:
        all_transactions.extend(chunk_result)
    
    logger.info(f"Total transactions before dedup: {len(all_transactions)}")
    
    # 2. 去重 - 基于日期、金额和描述的相似度
    seen = set()
    unique_transactions = []
    
    for tx in all_transactions:
        # 创建唯一键：日期_金额（取整到分）+ 描述前20字符
        date = tx.get('date', '')
        amount = tx.get('amount', 0)
        amount_key = round(amount, 2)  # 精确到分
        desc = tx.get('description', '')[:20].lower().strip()
        
        # 清理描述中的特殊字符
        desc = re.sub(r'[^a-z0-9]', '', desc)
        
        key = f"{date}_{amount_key}_{desc}"
        
        if key not in seen:
            seen.add(key)
            unique_transactions.append(tx)
    
    logger.info(f"Transactions after dedup: {len(unique_transactions)}")
    
    # 3. 按日期排序
    def sort_key(tx):
        date_str = tx.get('date', '')
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return datetime.min
    
    unique_transactions.sort(key=sort_key)
    
    return unique_transactions


def parse_pdf_with_chunking(
    pdf_bytes: bytes,
    provider: str = "openai",
    api_key: str = "",
    model: str = "",
    categories: Optional[List[Dict]] = None,
    pages_per_chunk: int = 3,
    max_chunks: int = 10,
) -> List[Dict[str, Any]]:
    """
    使用分块方式解析大型 PDF（避免 AI 超时）
    
    Args:
        pdf_bytes: PDF 文件字节数据
        provider: API 提供商 ("openai", "minimax", "google")
        api_key: API 密钥
        model: 模型名称
        categories: 分类列表
        pages_per_chunk: 每块包含的页数（默认 3 页）
        max_chunks: 最大分块数量（默认 10，防止无限分割）
        
    Returns:
        交易记录列表
    """
    # 获取 PDF 页数
    page_count = get_pdf_page_count(pdf_bytes)
    logger.info(f"PDF has {page_count} pages")
    
    # 如果页数小于等于 pages_per_chunk，直接解析
    if page_count <= pages_per_chunk:
        logger.info("PDF is small, parsing directly")
        return parse_pdf_with_ai(
            pdf_bytes=pdf_bytes,
            provider=provider,
            api_key=api_key,
            model=model,
            categories=categories
        )
    
    # 计算需要的分块数
    num_chunks = (page_count + pages_per_chunk - 1) // pages_per_chunk
    
    if num_chunks > max_chunks:
        # 如果分块太多，减少每块页数
        pages_per_chunk = (page_count + max_chunks - 1) // max_chunks
        num_chunks = (page_count + pages_per_chunk - 1) // pages_per_chunk
        logger.info(f"Adjusted pages_per_chunk to {pages_per_chunk} to fit max_chunks limit")
    
    # 分割 PDF
    chunks = split_pdf_by_pages(pdf_bytes, pages_per_chunk)
    logger.info(f"Split into {len(chunks)} chunks")
    
    # 创建解析器
    parser = create_parser(
        provider=provider,
        api_key=api_key,
        model=model,
        categories=categories
    )
    
    # 逐块解析
    results = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Parsing chunk {i+1}/{len(chunks)}")
        try:
            chunk_result = parser.parse(chunk)
            results.append(chunk_result)
            logger.info(f"Chunk {i+1}: extracted {len(chunk_result)} transactions")
        except Exception as e:
            logger.error(f"Failed to parse chunk {i+1}: {e}")
            # 继续处理其他块
            results.append([])
    
    # 合并结果
    merged = merge_transaction_results(results)
    logger.info(f"Final result: {len(merged)} transactions")
    
    return merged




def create_parser(
    provider: str = "openai",
    categories: Optional[List[Dict]] = None,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> AIAbstractParser:
    """
    创建 AI 解析器工厂函数

    Args:
        provider: API 提供商 ("openai" 或 "minimax")
        categories: 分类列表
        api_key: API 密钥
        model: 模型名称
        base_url: API 基础 URL

    Returns:
        AI 解析器实例
    """
    provider = provider.lower()

    if provider == "openai":
        return OpenAIParser(
            categories=categories,
            api_key=api_key,
            model=model or "gpt-4o",
            base_url=base_url or "https://api.openai.com/v1"
        )
    elif provider == "minimax":
        return MiniMaxParser(
            categories=categories,
            api_key=api_key,
            model=model or "abab6.5s-chat",
            base_url=base_url or "https://api.minimax.chat/v1"
        )
    elif provider in ["google", "gemini"]:
        return GoogleAIParser(
            categories=categories,
            api_key=api_key,
            model=model or "gemini-2.5-flash",
            base_url=base_url or "https://generativelanguage.googleapis.com"
        )
    else:
        raise ValueError(f"不支持的 API 提供商: {provider}")


# 便捷函数
def parse_pdf_with_ai(
    pdf_bytes: bytes,
    provider: str = "openai",
    api_key: str = "",
    model: str = "",
    categories: Optional[List[Dict]] = None,
    use_chunking: bool = True,
    chunk_pages: int = 3,
    max_chunks: int = 10,
) -> List[Dict[str, Any]]:
    """
    使用 AI 解析 PDF 账单

    Args:
        pdf_bytes: PDF 文件字节数据
        provider: API 提供商 ("openai", "minimax", "google")
        api_key: API 密钥
        model: 模型名称
        categories: 分类列表
        use_chunking: 是否使用分块处理（默认 True，大 PDF 自动分块）
        chunk_pages: 每块的页数（默认 3）
        max_chunks: 最大分块数（默认 10）

    Returns:
        交易记录列表
    """
    # 自动检测是否需要分块
    if use_chunking:
        page_count = get_pdf_page_count(pdf_bytes)
        # 如果页数大于 chunk_pages 或超过 5 页，建议使用分块
        if page_count > chunk_pages or page_count > 5:
            logger.info(f"Using chunking for PDF with {page_count} pages")
            return parse_pdf_with_chunking(
                pdf_bytes=pdf_bytes,
                provider=provider,
                api_key=api_key,
                model=model,
                categories=categories,
                pages_per_chunk=chunk_pages,
                max_chunks=max_chunks,
            )
    
    # 小 PDF 直接解析
    parser = create_parser(
        provider=provider,
        api_key=api_key,
        model=model,
        categories=categories
    )
    return parser.parse(pdf_bytes)


# ========== 兼容层 ==========

class AITransaction:
    """AI 解析的交易记录（兼容格式）"""
    
    def __init__(
        self,
        date: str,  # AI 返回的是字符串
        amount: float,
        description: str,
        type: str,
        category: Optional[str] = None,
        confidence: float = 0.9
    ):
        self.date = date
        self.amount = amount
        self.description = description
        self.type = type
        self.category = category
        self.confidence = confidence


class GoogleAIParser(AIAbstractParser):
    """Google Gemini API 解析器"""

    def __init__(
        self,
        categories: Optional[List[Dict]] = None,
        api_key: str = "",
        model: str = "gemini-2.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com",
    ):
        self.categories = categories or []
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()

    def parse(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """使用 Google Gemini API 解析 PDF"""
        # 将 PDF 转为 base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # 构建提示词
        prompt = self._get_system_prompt() + "\n\n" + self._get_user_prompt("请解析这个银行 PDF 账单，提取所有交易记录。")

        headers = {"Content-Type": "application/json"}
        
        # Gemini API 格式 - 使用 v1beta 端点
        # 注意：需要将 PDF 作为 media 文件上传，或使用 inline data
        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "maxOutputTokens": 32768,
                "temperature": 0.1,
            }
        }

        # API URL 格式
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"

        response = self._session.post(
            url,
            headers=headers,
            json=payload,
            params={"key": self.api_key},
            timeout=120
        )
        
        if response.status_code != 200:
            logger.error(f"Gemini API 错误: {response.status_code} - {response.text}")
            raise RuntimeError(f"Gemini API 错误: {response.status_code} - {response.text}")

        result = response.json()
        
        # 调试：打印完整响应
        logger.info(f"Gemini 响应: {result}")
        
        # 尝试多种响应格式
        try:
            # 格式1: candidates[0].content.parts[0].text
            if "candidates" in result and result["candidates"]:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return self._extract_json(text)
        except (KeyError, IndexError, TypeError):
            pass
        
        try:
            # 格式2: promptFeedback (可能是blocked)
            if "promptFeedback" in result:
                raise RuntimeError(f"内容被阻止: {result.get('promptFeedback', {})}")
        except (KeyError, IndexError, TypeError):
            pass
        
        # 如果都失败，抛出详细错误
        logger.error(f"无法解析 Gemini 响应格式: {result}")
        raise RuntimeError(f"无法从响应中提取 JSON 数据: {result}")

    def _extract_json(self, content: str) -> List[Dict[str, Any]]:
        """从响应中提取 JSON"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r'(\[[\s\S]*)', content)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复截断的 JSON
                fixed = self._extract_partial_json(json_str)
                if fixed:
                    return fixed
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise RuntimeError("无法从响应中提取 JSON 数据")

    def _extract_partial_json(self, json_str: str) -> List[Dict[str, Any]]:
        """从可能被截断的 JSON 内容中提取尽可能多的完整对象"""
        import logging
        
        objects = []
        
        # 找到数组开始
        array_start = json_str.find('[')
        if array_start != -1:
            json_str = json_str[array_start:]
        
        # 添加缺失的 ]
        if json_str.count('[') > json_str.count(']'):
            json_str += ']'
        
        # 直接尝试解析
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]
        except json.JSONDecodeError:
            pass
        
        # 尝试分割成对象并逐个解析
        parts = json_str.split('}')
        
        for part in parts[:-1]:  # 跳过最后一个（可能被截断）
            if not part.strip().startswith('{'):
                continue
            part += '}'
            try:
                obj = json.loads(part)
                objects.append(obj)
            except json.JSONDecodeError:
                # 尝试修复：移除最后一个逗号后的内容
                last_comma = part.rfind(',')
                if last_comma != -1:
                    fixed = part[:last_comma] + '}'
                    try:
                        obj = json.loads(fixed)
                        objects.append(obj)
                    except:
                        pass
        
        if objects:
            logging.getLogger(__name__).info(f"从截断的响应中提取了 {len(objects)} 条交易记录")
            return objects
        
        return None


class PDFAIParser:
    """
    AI 解析器（兼容旧接口）
    
    使用配置中的 AI 设置来解析 PDF
    支持分块处理大型 PDF
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.ai_config = config.get("ai", {}).get("pdf_parser", {})
        
        if not self.ai_config.get("enabled"):
            raise ValueError("AI 解析未启用，请在 config.yaml 中配置")
        
        self.api_key = self.ai_config.get("api_key", "")
        self.provider = self.ai_config.get("provider", "openai")
        self.model = self.ai_config.get("model", "")
        
        # 分块处理配置
        self.use_chunking = self.ai_config.get("use_chunking", True)
        self.chunk_pages = self.ai_config.get("chunk_pages", 3)
        self.max_chunks = self.ai_config.get("max_chunks", 10)
        
        # 获取分类
        from core.database import Database
        db_path = config.get("database.path", "data/expenses.db")
        db = Database(db_path)
        self.categories = db.get_categories()
    
    def parse_pdf_bytes(self, pdf_bytes: bytes) -> List[AITransaction]:
        """解析 PDF，返回交易列表（支持分块）"""
        raw_transactions = parse_pdf_with_ai(
            pdf_bytes=pdf_bytes,
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
            categories=self.categories,
            use_chunking=self.use_chunking,
            chunk_pages=self.chunk_pages,
            max_chunks=self.max_chunks,
        )
        
        # 转换为 AITransaction 对象
        transactions = []
        for tx in raw_transactions:
            transactions.append(AITransaction(
                date=tx.get('date', ''),
                amount=float(tx.get('amount', 0)),
                description=tx.get('description', ''),
                type=tx.get('type', 'expense'),
                category=tx.get('category'),
                confidence=0.9
            ))
        
        return transactions


def create_ai_parser(config: dict) -> PDFAIParser:
    """
    创建 AI 解析器（兼容函数）
    
    Args:
        config: 应用配置
        
    Returns:
        PDFAIParser 实例
    """
    return PDFAIParser(config)
