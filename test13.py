import matplotlib.pyplot as plt

# Data
bars = [
    {"name": "LangChain", "value": 212, "color": "#ff6b6b"},
    {"name": "COOP",      "value": 70,  "color": "#4ecdc4"}
]

# Extract data for plotting
names = [bar["name"] for bar in bars]
values = [bar["value"] for bar in bars]
colors = [bar["color"] for bar in bars]

# Plot
plt.figure(figsize=(6, 5))
plt.bar(names, values, color=colors)

# Labels and title
plt.xlabel('Approach')
plt.ylabel('Lines of Code (LOC)')
plt.title('Business Code LOC Comparison')

# Optional: add value labels on top of bars
for i, v in enumerate(values):
    plt.text(i, v + 5, str(v), ha='center', va='bottom', fontsize=10)

# Display
plt.tight_layout()
plt.show()