import io
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def test():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Test Rupee: \u20b9 100", styles['Normal']))
    doc.build(elements)
    print("Done")

test()
