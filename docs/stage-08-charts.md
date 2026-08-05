# Stage 08: Charts

## Features implemented in this stage
- Added an inline button "View Chart" to the monthly stats view.
- Built a chart generation service using matplotlib to render a pie chart of the user's category breakdown.
- Charts are rendered into an in-memory PNG buffer and sent to the user as a Telegram photo without touching the disk.

## Commands run
```bash
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python -c "from bot.services.charts import generate_pie_chart..."
git add .
git commit -m "Added pie chart generation for expenses in the stats command"
git push
```

## Code built

`requirements.txt`
```text
aiogram>=3.0,<4.0
aiosqlite>=0.19.0
python-dotenv>=1.0.0
python-dateutil>=2.8.2
matplotlib>=3.7.0
```
This was updated to fix a mangled package name and to add `matplotlib`, which is required for our chart generation.

`bot/services/charts.py`
```python
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
```
This file contains the logic to draw the pie chart. We specifically use the `Agg` backend because the bot runs on a server without a GUI. We format the chart as a donut and save it directly into an `io.BytesIO()` buffer, returning the bytes so we never have to manage deleting temporary files from the disk ([charts.py](file:///c:/Users/KIIT0001/Desktop/PennyPilot/bot/services/charts.py)).

`bot/handlers/stats.py`
```python
class StatsChartCb(CallbackData, prefix="stats_chart"):
    start_date: str
    end_date: str
```
We added a new callback data class for the chart button.

In `cb_stats_month`:
```python
    builder = InlineKeyboardBuilder()
    if sorted_cats:
        builder.button(
            text="📊 View Chart",
            callback_data=StatsChartCb(start_date=start_date, end_date=end_date).pack()
        )
    builder.button(text="⬅️ Back to Months", callback_data="stats_back")
    builder.adjust(1)
```
We added the button to trigger the chart generation, only showing it if there are actually expenses to chart.

```python
@router.callback_query(StatsChartCb.filter())
async def cb_stats_chart(query: CallbackQuery, callback_data: StatsChartCb) -> None:
    """Send a pie chart of the month's expenses."""
    ...
    # Generate chart
    from bot.services.charts import generate_pie_chart
    chart_bytes = generate_pie_chart(cat_totals)
    
    # Send photo
    from aiogram.types import BufferedInputFile
    photo = BufferedInputFile(chart_bytes, filename="chart.png")
    ...
```
This is the handler that actually intercepts the "View Chart" button press, fetches the transactions again for the period, aggregates the expenses by category, calls our `generate_pie_chart` service, and uses `BufferedInputFile` to send the in-memory bytes back to Telegram as a photo ([stats.py](file:///c:/Users/KIIT0001/Desktop/PennyPilot/bot/handlers/stats.py#L159-L198)).

## Interview Q&A

**Q: Why use matplotlib instead of just sending the user a web link to a chart?**
A: Sending a rendered image directly into the chat keeps the user within Telegram, providing a much smoother and self-contained experience. It also prevents us from needing to host a separate web service just to display charts.

**Q: Why use the `Agg` backend in matplotlib?**
A: Matplotlib is designed with various backends, some of which try to open GUI windows (like Tkinter). By explicitly setting the backend to `Agg`, we tell matplotlib to only render images to memory/files, avoiding crashes on a headless server.

**Q: Why generate the image into an in-memory buffer instead of a temporary file?**
A: Writing to disk requires managing file permissions, cleaning up files after they are sent, and handling concurrent writes if multiple users request charts at once. Using `io.BytesIO()` avoids all I/O overhead and cleans up automatically when the function finishes.

**Q: What happens if there are too many categories for the chart colors?**
A: The script duplicates the color palette if the number of slices exceeds the available distinct colors. In practice, our bot design discourages over-categorization, so a user should typically have fewer than 10 categories, making the colors easy to distinguish.

**Q: Does creating charts block the async event loop?**
A: Matplotlib is synchronous, so generating a very complex chart could theoretically block the loop for a fraction of a second. For our simple pie chart, it's fast enough not to be an issue, but for a high-traffic bot, we'd offload this to an asyncio executor.
