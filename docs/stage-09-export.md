# Stage 09: Export

## Features implemented in this stage
- Added an interactive `/export` command to let users download their transaction data via inline keyboards.
- Built a full CSV export of all historical transactions using Python's built-in `csv` module.
- Built a monthly PDF statement generator using `reportlab`.
- **PDF Layout:** Includes a large bold title for the statement month, a bolded summary of "Total Income", "Total Expenses", and "Net Balance". Underneath, there is a grid-styled table featuring alternating background colors (grey header, beige rows) with columns for Date, Type, Category, Amount, and Note. 
- **Important Rendering Note:** ReportLab's default Helvetica font maps to `WinAnsiEncoding` which does *not* support the UTF-8 Indian Rupee symbol (`₹`). Because embedding custom TrueType Fonts (TTFs) adds unnecessary bloat to a v1 minimal bot, we explicitly replaced the `₹` symbol with `Rs.` in the PDF rendering pipeline to prevent "black square" rendering bugs.
- **In-Memory Streams:** All generation uses `io.StringIO` (for CSV) and `io.BytesIO` (for PDF) so files are rendered entirely in RAM and immediately piped to Telegram. No disk I/O occurs, preventing storage bloat and ensuring maximum privacy.

## Code Built

`bot/services/export.py`
This service handles all document generation, isolating the business logic from the Telegram interface. We use `io.StringIO` for the CSV and `io.BytesIO` for the PDF so that everything is rendered purely in memory. The PDF uses ReportLab's `Platypus` layout engine to render a well-formatted table and summary paragraphs.

`bot/handlers/export.py`
This module acts as the router. It parses the `/export` command, dynamically calculates the user's past 3 financial months (based on their custom `month_start_day`), and constructs an `InlineKeyboardBuilder`. 
When a user clicks a PDF button, it fetches transactions, calculates net summaries, and calls our `generate_pdf` service. We use aiogram's `BufferedInputFile` to directly stream the byte-buffer into Telegram as a document, avoiding any temporary files.

`main.py`
We added `export_router` to our dispatcher and added `export` to the bot's default commands menu so users can easily discover the feature.

## Interview Q&A

**Q: Why use `reportlab` over something simpler like generating HTML and converting it to PDF?**
A: `reportlab` is a robust, pure-Python library that draws directly to a PDF canvas without needing a heavy browser engine (like wkhtmltopdf or Puppeteer) installed on the server. This makes our bot extremely lightweight and easy to deploy on free-tier infrastructure.

**Q: How do you handle file cleanup after sending the export?**
A: We don't have to! By using `io.StringIO` for CSV and `io.BytesIO` for PDF, the files are generated directly into the server's RAM. Aiogram sends those bytes directly to Telegram, and Python's garbage collector frees the memory immediately after. No disk I/O means no leftover files.

**Q: What happens if a user exports a CSV and they have thousands of transactions?**
A: Generating a CSV is incredibly fast and memory-efficient in Python. However, fetching all rows at once into memory might become a bottleneck for users with tens of thousands of rows. For a production app with huge data, we would stream the database cursor directly to the CSV writer instead of loading it all into a list first.

**Q: Why separate the PDF/CSV logic into `bot/services/export.py` rather than putting it in the handler?**
A: Separation of concerns. Handlers should only deal with Telegram-specific logic (receiving messages, answering queries). The actual generation of a PDF is a business logic service that could theoretically be reused in a web dashboard or email script later without depending on aiogram.
