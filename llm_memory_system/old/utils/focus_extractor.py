# utils/focus_extractor.py
# 为简化，我们直接返回输入，实际可使用jieba等分词工具
def extract_focus_keywords(text: str, top_k: int = 5) -> str:
    # 示例：取前5个词作为焦点
    words = text.split()[:top_k]
    return " ".join(words)



