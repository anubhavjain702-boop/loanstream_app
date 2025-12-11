# pdf_generator.py
# Simple PDF generator using fpdf2
from fpdf import FPDF
import os
import datetime

def generate_application_pdf(app_data: dict, output_dir: str = "uploads") -> str:
    """
    app_data = {
      "app_id": "APP123",
      "name": "Ramesh",
      "sanction_id": "SAN001",
      "loan_amount": 500000,
      "tenure_months": 60,
      ...
    }
    Returns path to generated pdf file.
    """
    # ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)

    app_id = app_data.get("app_id", f"app_{int(datetime.datetime.now().timestamp())}")
    filename = f"{app_id}.pdf"
    filepath = os.path.join(output_dir, filename)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=16, style="B")
    pdf.cell(0, 10, "LoanStream - Loan Application", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Arial", size=12)
    # Add key-values
    for key, val in app_data.items():
        # convert complex objects to string
        if isinstance(val, (list, dict)):
            val = str(val)
        pdf.multi_cell(0, 8, f"{str(key).capitalize()}: {str(val)}")
        pdf.ln(1)

    pdf.ln(8)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)

    pdf.output(filepath)
    return filepath


    c.showPage()
    c.save()
    return output_path

