# pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import io
from datetime import datetime

def calculate_emi(principal, annual_rate, months):
    if months <= 0:
        return 0.0
    r = (annual_rate / 100) / 12.0
    if r == 0:
        return principal / months
    emi = (principal * r * (1 + r) ** months) / ((1 + r) ** months - 1)
    return round(emi, 2)

def generate_sanction_pdf(application, user, output_path):
    """
    application: loan application object (SQLAlchemy)
    user: user object
    output_path: filename to save pdf to (e.g., "APPxxxx_sanction.pdf")
    """
    # create simple PDF using reportlab
    c = canvas.Canvas(output_path, pagesize=A4)
    w, h = A4
    left = 20 * mm
    top = h - 20 * mm

    c.setFont("Helvetica-Bold", 18)
    c.drawString(left, top, "Sanction Letter")
    c.setFont("Helvetica", 11)
    c.drawString(left, top - 20, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
    c.drawString(left, top - 40, f"Applicant: {user.name or user.email}")
    c.drawString(left, top - 60, f"Application ID: {application.app_id}")
    c.drawString(left, top - 80, f"Loan Amount: ₹{application.loan_amount:,.2f}")
    c.drawString(left, top - 100, f"Tenure (months): {application.tenure_months}")
    c.drawString(left, top - 120, f"Interest rate (annual): {application.annual_rate}%")
    emi = calculate_emi(application.loan_amount or 0, application.annual_rate or 0, application.tenure_months or 1)
    c.drawString(left, top - 140, f"Estimated EMI: ₹{emi:,.2f} per month")
    c.drawString(left, top - 180, "Decision:")
    c.setFont("Helvetica", 10)
    c.drawString(left, top - 200, application.decision_reason or "Approved")

    c.setFont("Helvetica", 9)
    c.drawString(left, 30 * mm, "This is a system generated sanction letter.")

    c.showPage()
    c.save()
    return output_path
