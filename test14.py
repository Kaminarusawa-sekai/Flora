import matplotlib.pyplot as plt
import numpy as np

# Data in English
metrics = ["Difficulty", "Effort", "Estimated Bugs"]
langchain_values = [118.39, 839123, 2.36]
coop_values = [0, 0, 0]  # All zero as per your data

# Colors
color_langchain = "#ff6b6b"
color_coop = "#4ecdc4"

# Number of metrics
n_metrics = len(metrics)
y_positions = np.arange(n_metrics)
bar_height = 0.35  # Height of each bar

# Create horizontal grouped bar chart
fig, ax = plt.subplots(figsize=(8, 5))

bars1 = ax.barh(y_positions + bar_height/2, langchain_values, 
                height=bar_height, label='LangChain', color=color_langchain)
bars2 = ax.barh(y_positions - bar_height/2, coop_values, 
                height=bar_height, label='COOP', color=color_coop)

# Labels and title
ax.set_xlabel('Complexity Value')
ax.set_ylabel('Halstead Metric')
ax.set_title('Halstead Complexity Comparison')
ax.set_yticks(y_positions)
ax.set_yticklabels(metrics)
ax.legend()

# Optional: add value labels on bars (only for non-zero values)
for bar in bars1:
    width = bar.get_width()
    if width > 0:
        ax.text(width + max(langchain_values) * 0.01, bar.get_y() + bar.get_height()/2,
                f'{width:.2f}' if width < 1000 else f'{int(width)}',
                va='center', ha='left', fontsize=9)

# Improve layout
plt.tight_layout()
plt.show()