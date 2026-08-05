"""
Service for exporting transactions to CSV and PDF.
"""
import io
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_csv(transactions: list[dict]) -> bytes:
    """
    Generate a CSV containing all transactions.
    Returns bytes of the CSV file.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["ID", "Date", "Category", "Type", "Amount", "Note", "Created At"])
    
    for t in transactions:
        writer.writerow([
            t["id"],
            t["date"],
            t["category_name"],
            t["type"],
            t["amount"],
            t.get("note", ""),
            t["created_at"]
        ])
        
    return output.getvalue().encode('utf-8')

def generate_pdf(transactions: list[dict], month_label: str, summary: dict) -> bytes:
    """
    Generate a monthly PDF statement using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], spaceAfter=14, alignment=1
    )
    elements.append(Paragraph(f"Financial Statement: {month_label}", title_style))
    
    # Summary Section
    summary_text = (
        f"<b>Total Income:</b> Rs.{summary['income']:,.2f}<br/>"
        f"<b>Total Expenses:</b> Rs.{summary['expenses']:,.2f}<br/>"
        f"<b>Net Balance:</b> Rs.{summary['net']:,.2f}"
    )
    elements.append(Paragraph(summary_text, styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))
    
    # Transactions Table
    if not transactions:
        elements.append(Paragraph("No transactions recorded for this period.", styles['Normal']))
    else:
        # Table Header
        data = [["Date", "Type", "Category", "Amount", "Note"]]
        
        # Table Rows
        for t in transactions:
            data.append([
                t["date"],
                t["type"].capitalize(),
                t["category_name"],
                f"Rs.{t['amount']:,.2f}",
                t.get("note", "") or ""
            ])
            
        table = Table(data, colWidths=[1 * inch, 0.8 * inch, 1.2 * inch, 1 * inch, 2 * inch])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Amount right-aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
        
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
