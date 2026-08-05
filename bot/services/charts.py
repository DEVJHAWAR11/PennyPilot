"""
Chart generation service using matplotlib.
"""
import io
import matplotlib
# Use Agg backend to avoid GUI requirement and run purely in memory
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_pie_chart(category_totals: dict[str, float]) -> bytes:
    """
    Generate a pie chart from category totals.
    Returns the PNG image as bytes.
    """
    if not category_totals:
        return b""
        
    # Sort data for better presentation (largest first)
    sorted_data = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in sorted_data]
    sizes = [item[1] for item in sorted_data]
    
    # Modern color palette
    colors = plt.cm.Set3.colors
    if len(sizes) > len(colors):
        # repeat if we have too many categories
        colors = list(colors) * (len(sizes) // len(colors) + 1)
    
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Create the pie chart
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=labels, 
        autopct='%1.1f%%', 
        startangle=90,
        colors=colors,
        wedgeprops=dict(width=0.4, edgecolor='w') # Donut chart style
    )
    
    plt.setp(autotexts, size=10, weight="bold")
    plt.setp(texts, size=11)
    
    ax.set_title("Expenses Breakdown", fontsize=16, weight="bold", pad=20)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close(fig)
    
    buf.seek(0)
    return buf.read()
