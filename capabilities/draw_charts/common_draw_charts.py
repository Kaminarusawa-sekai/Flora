import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any, Dict, List, Union
from .interface import IChartDrawer


class CommonChartDrawer(IChartDrawer):
    """
    通用图表绘制能力的实现类，实现了IChartDrawer接口
    提供将查询结果转换为可视化图表的具体实现
    """
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化图表绘制能力
        """
        self._initialized = True
    
    def shutdown(self) -> None:
        """
        关闭图表绘制能力
        """
        self._initialized = False
    
    def enhance_with_charts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        对 resolve_context 的结果进行后处理：
          - 若某个 value 是 list[dict]（即查询结果 records），
            且满足可视化条件，则将其替换为 Plotly 图表 HTML 字符串。
          - 其他值（单值、None、非列表）保持不变。
        """
        enhanced = {}
        
        for key, value in result.items():
            # 只处理 list[dict] 类型（即 Vanna 返回的多行结果）
            if not isinstance(value, list) or not value:
                enhanced[key] = value
                continue

            try:
                df = pd.DataFrame(value)
                
                # 安全限制：避免大数据绘图
                if len(df) > 1000:
                    enhanced[key] = value  # 保持原样
                    continue

                numeric_cols = df.select_dtypes(include='number').columns.tolist()
                time_like_cols = [
                    col for col in df.columns 
                    if any(kw in str(col).lower() for kw in ['date', 'time', 'month', 'year', 'dt', 'ym', 'day'])
                ]
                categorical_cols = [col for col in df.columns if col not in numeric_cols]

                fig = None

                # === 策略 1：时间序列（优先）===
                if time_like_cols and numeric_cols:
                    x_col = time_like_cols[0]
                    y_cols = numeric_cols[:2]  # 最多两个指标，支持双轴
                    if len(y_cols) == 1:
                        fig = px.line(df, x=x_col, y=y_cols[0], title=key)
                    else:
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        fig.add_trace(
                            go.Scatter(x=df[x_col], y=df[y_cols[0]], mode='lines+markers', name=y_cols[0]),
                            secondary_y=False
                        )
                        fig.add_trace(
                            go.Scatter(x=df[x_col], y=df[y_cols[1]], mode='lines+markers', name=y_cols[1]),
                            secondary_y=True
                        )
                        fig.update_layout(title=key)

                # === 策略 2：分类柱状图 ===
                elif len(categorical_cols) >= 1 and numeric_cols and len(df) <= 50:
                    x_col = categorical_cols[0]
                    y_col = numeric_cols[0]
                    fig = px.bar(df, x=x_col, y=y_col, title=key)

                # === 策略 3：散点图（两数值列）===
                elif len(numeric_cols) >= 2 and len(df) <= 200:
                    fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], title=key)

                # === 策略 4：单数值列 + 分类 → 柱状图 ===
                elif len(numeric_cols) == 1 and len(categorical_cols) >= 1 and len(df) <= 100:
                    fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0], title=key)

                # 如果生成了图表
                if fig is not None:
                    # 生成可嵌入 HTML 的片段（轻量、CDN 加载 Plotly.js）
                    chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                    enhanced[key] = chart_html
                else:
                    enhanced[key] = value  # 无法可视化，保留原始数据

            except Exception as e:
                # 任何异常都 fallback 到原始数据，保证稳定性
                enhanced[key] = value

        return enhanced



