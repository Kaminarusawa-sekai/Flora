import json
from bs4 import BeautifulSoup

import html

def extract_data_config(html_str):
    """
    从包含 dplayer 的 div 中提取 data-config 并转为正常 dict。
    
    Args:
        html_str (str): 包含 <div class="dplayer" data-config="..."> 的 HTML 字符串
    
    Returns:
        dict: 解析后的配置字典，包含 video.url 等字段
        None: 如果未找到或解析失败
    """
    soup = BeautifulSoup(html_str, 'html.parser')
    div = soup.find('div', class_='dplayer')
    
    if not div or not div.get('data-config'):
        print("❌ 未找到带有 data-config 的 dplayer 元素")
        return None

    # 获取 data-config 原始字符串（含 &quot;）
    config_str = div['data-config']
    
    # 将 HTML 实体（如 &quot;）转回正常字符
    unescaped_str = html.unescape(config_str)
    
    try:
        config_dict = json.loads(unescaped_str)
        return config_dict
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"原始内容: {unescaped_str}")
        return None

# ===== 示例使用 =====
if __name__ == "__main__":
    # 你的 HTML 片段（可替换成从文件或网络获取的内容）
    html_input = '''



'''

    config = extract_data_config(html_input)
    
    if config:
        print("✅ 成功解析 data-config:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        
        # 提取视频链接
        video_url = config.get("video", {}).get("url")
        if video_url:
            print(f"\n🎥 视频链接: {video_url}")


