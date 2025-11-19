from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re

@dataclass
class Option:
    idx: int               # 1-based index
    code: str              # canonical short code
    label: str             # display label
    synonyms: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

@dataclass
class SemanticMatchResult:
    chosen_index: Optional[int]
    confidence: float
    reason: str
    strategy: str  # 'keyword' | 'fallback' | 'none'

class OptionBuilder:
    """根据阶段与上下文构造可选项列表 (本地结构, 不调用 LLM)"""
    @staticmethod
    def build(stage: str, context: Dict) -> List[Option]:
        size = context.get('current_size') or (context.get('_manager') and context.get('_manager').get_context().get('current_size'))
        series = context.get('current_series') or (context.get('_manager') and context.get('_manager').get_context().get('current_series'))
        if stage == 'chip_select' and series == 'MacBook Pro':
            if size == '14寸':
                return [
                    Option(1, 'm3', 'M3', ['基础性能','入门','低功耗'], ['基础','入门','低功耗']),
                    Option(2, 'm3_pro', 'M3 Pro', ['多核','编译','创作','中高性能'], ['多核','性能','编译','创作']),
                    Option(3, 'm3_max', 'M3 Max', ['最高性能','渲染','剪辑','重度'], ['最高','4k','剪辑','渲染','重度'])
                ]
            else:  # 16寸 (只展示 Pro / Max)
                return [
                    Option(1, 'm3_pro', 'M3 Pro', ['多核','编译','创作','较高性能'], ['多核','性能','编译','创作']),
                    Option(2, 'm3_max', 'M3 Max', ['最高性能','渲染','剪辑','重度'], ['最高','4k','剪辑','渲染','重度'])
                ]
        if stage == 'storage_select':
            # 简化：根据系列 & 芯片推断常见容量顺序
            selected_chip = context.get('selected_chip') or (context.get('_manager') and context.get('_manager').get_context().get('selected_chip'))
            # 统一映射：1=512GB 2=1TB 3=2TB
            return [
                Option(1, '512', '512GB', ['五百一十二','五一二','半T','基础容量'], ['512','半','基础','低容量']),
                Option(2, '1tb', '1TB', ['一T','一兆','中等容量','升级'], ['1t','一t','中等','升级','扩展']),
                Option(3, '2tb', '2TB', ['两T','双T','最大容量','高容量'], ['2t','二t','双','更大','最大','高容量'])
            ]
        if stage == 'color_select':
            # 通用颜色选项示例，需与实际模板顺序对应
            return [
                Option(1, 'space_gray', '深空灰', ['灰色','灰','深灰','暗灰'], ['灰','深空','暗灰']),
                Option(2, 'silver', '银色', ['银白','银','亮银','白银'], ['银','银色','银白']),
                Option(3, 'midnight', '午夜色', ['午夜','深蓝','暗蓝'], ['午夜','深蓝','暗蓝']),
                Option(4, 'starlight', '星光色', ['星光','香槟','浅金','淡金'], ['星光','香槟','金'])
            ]
        if stage == 'phone_model_select':
            # 仅苹果手机型号语义映射
            return [
                Option(1, 'iphone16pro', 'iPhone 16 Pro 系列', ['旗舰','专业','高端','顶配','pro','pro max','钛','自然钛','摄影','剪辑'], ['旗舰','专业','高端','顶配','pro','max','钛','摄影','剪辑']),
                Option(2, 'iphone16', 'iPhone 16 系列', ['标准版','均衡','普通','日常','plus','16'], ['标准','均衡','普通','日常','plus','16']),
                Option(3, 'iphone15', 'iPhone 15 系列', ['上一代','旧款','便宜','性价比','15'], ['上一代','旧款','便宜','性价比','15'])
            ]
        if stage == 'phone_storage_select':
            # 根据当前系列返回容量选项
            if series == 'iPhone 16 Pro 系列':
                return [
                    Option(1, '256gb', '256GB', ['基础','入门','较小'], ['256','基础','入门','较小']),
                    Option(2, '512gb', '512GB', ['中等','均衡','够用'], ['512','中等','均衡','够用']),
                    Option(3, '1tb', '1TB', ['最大','顶配','超大','高端'], ['1tb','1t','最大','顶配','超大','高端'])
                ]
            else:  # 16 / 15 系列
                return [
                    Option(1, '128gb', '128GB', ['基础','入门','最低'], ['128','基础','入门','最低']),
                    Option(2, '256gb', '256GB', ['中等','均衡','够用'], ['256','中等','均衡','够用']),
                    Option(3, '512gb', '512GB', ['大容量','更大','高端'], ['512','大','更大','高端'])
                ]
        if stage == 'phone_color_select':
            return [
                Option(1, 'black', '黑色', ['黑','深色','暗色'], ['黑','黑色','暗']),
                Option(2, 'white', '白色', ['白','亮白','纯白'], ['白','白色','亮白']),
                Option(3, 'blue', '蓝色', ['蓝','深蓝','亮蓝'], ['蓝','蓝色','深蓝']),
                Option(4, 'natural_titanium', '自然钛', ['钛','自然钛','钛合金','自然'], ['钛','自然','自然钛'])
            ]
        # 其他阶段暂未接入语义映射
        return []

class SemanticMapper:
    """本地语义映射实现: 只做关键词与同义词简单打分"""
    @staticmethod
    def map(user_text: str, options: List[Option]) -> SemanticMatchResult:
        text = user_text.lower().strip()
        if not text:
            return SemanticMatchResult(None, 0.0, '空输入', 'none')
        # 简单正则清理
        cleaned = re.sub(r'[!！?？,，。]+', ' ', text)
        # 评分：关键词命中2分（子串匹配），synonym命中1分
        best: Tuple[Optional[int], float, str] = (None, 0.0, '')
        for opt in options:
            score = 0.0
            hit_words = []
            for k in opt.keywords:
                kl = k.lower()
                if kl and kl in cleaned:
                    score += 2
                    hit_words.append(k)
            for s in opt.synonyms:
                sl = s.lower()
                if sl and sl in cleaned:
                    # 若关键词已命中避免重复加分
                    if s not in hit_words:
                        score += 1
                        hit_words.append(s)
            if score > best[1]:
                best = (opt.idx, score, ','.join(hit_words))
        if best[0] is None:
            return SemanticMatchResult(None, 0.0, '无匹配', 'none')
        # 简单归一化：理论最大 = 该选项关键词数量*2
        max_possible = (len(options[best[0]-1].keywords) * 2) or 1
        confidence = min(1.0, (best[1] / max_possible) if max_possible else 0.0)
        # 低置信度阈值 0.25 视为不确定
        if confidence < 0.25:
            return SemanticMatchResult(None, confidence, f'匹配分数低({confidence:.2f})', 'none')
        return SemanticMatchResult(best[0], confidence, f'命中:{best[2]} 分:{best[1]}', 'keyword')
