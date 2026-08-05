from bot.services.export import generate_pdf, generate_csv
import os

transactions = [
    {"id": 1, "date": "2026-08-01", "category_name": "Groceries", "type": "expense", "amount": 142.35, "note": "Walmart", "created_at": "2026-08-01T10:00:00"},
    {"id": 2, "date": "2026-08-02", "category_name": "Salary", "type": "income", "amount": 52500.0, "note": "August Pay", "created_at": "2026-08-02T10:00:00"}
]
summary = {"income": 52500.0, "expenses": 142.35, "net": 52357.65}

pdf_bytes = generate_pdf(transactions, "Aug 2026", summary)
csv_bytes = generate_csv(transactions)

with open("test.pdf", "wb") as f:
    f.write(pdf_bytes)

with open("test.csv", "wb") as f:
    f.write(csv_bytes)

print(f"PDF size: {len(pdf_bytes)}, CSV size: {len(csv_bytes)}")
