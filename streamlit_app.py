# streamlit_app.py
import streamlit as st
from database import init_db, SessionLocal, User, LoanApplication, KYC, AuditLog, generate_id, UPLOAD_DIR
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os
from pdf_generator import generate_sanction_pdf, calculate_emi
from datetime import datetime

load_dotenv()
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_user(db: Session, email, password, name=None, phone=None, is_admin=False):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None
    u = User(email=email, name=name, phone=phone, is_admin=is_admin)
    u.set_password(password)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def get_user_by_email(db: Session, email):
    return db.query(User).filter(User.email == email).first()

def submit_application(db: Session, user: User, loan_amount, tenure_months, annual_rate, income_monthly, employment_type):
    app = LoanApplication(
        app_id=generate_id("APP"),
        user_id=user.id,
        status="Submitted",
        loan_amount=loan_amount,
        tenure_months=tenure_months,
        annual_rate=annual_rate,
        income_monthly=income_monthly,
        employment_type=employment_type
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    db.add(AuditLog(event="application_submitted", payload=f"{user.email} -> {app.app_id}"))
    db.commit()
    return app

def save_kyc(db: Session, application: LoanApplication, uploaded_file):
    fname = f"{application.app_id}_{uploaded_file.name}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    k = KYC(application_id=application.id, filename=fname)
    db.add(k)
    db.commit()
    db.refresh(k)
    return k

def run_underwriting(application: LoanApplication, db: Session):
    income = application.income_monthly or 0
    score_base = min(850, int(300 + (income / 1000) + (application.tenure_months or 12)))
    credit_score = score_base
    emi = calculate_emi(application.loan_amount or 0, application.annual_rate or 12.0, application.tenure_months or 12)
    dti = emi / (income + 1e-6)
    reasons = []
    approved = True
    if income < 8000:
        approved = False
        reasons.append("Monthly income below minimum threshold (₹8,000).")
    if credit_score < 600:
        approved = False
        reasons.append(f"Credit score too low ({credit_score}).")
    if dti > 0.5:
        approved = False
        reasons.append(f"High debt-to-income ratio ({dti:.2f}).")
    if approved:
        application.status = "Approved"
        application.sanction_id = generate_id("SAN")
        application.decision_reason = "Meets automated underwriting criteria."
    else:
        application.status = "Rejected"
        application.decision_reason = " | ".join(reasons)
    application.credit_score = credit_score
    application.dti = dti
    db.add(application)
    db.commit()
    db.refresh(application)
    db.add(AuditLog(event="underwriting_run", payload=f"{application.app_id} -> {application.status}"))
    db.commit()
    return application

st.set_page_config(page_title="LoanStream", layout="centered", initial_sidebar_state="expanded")
if "current_user" not in st.session_state:
    st.session_state.current_user = None

menu = ["Home", "Apply", "Upload KYC", "Status", "Admin"]
choice = st.sidebar.selectbox("Menu", menu)

with st.sidebar.expander("Account"):
    if st.session_state.current_user:
        st.write("Logged in as:", st.session_state.current_user.email)
        if st.button("Logout"):
            st.session_state.current_user = None
            st.experimental_rerun()
    else:
        auth_mode = st.radio("Action", ("Login", "Signup"))
        email = st.text_input("Email", key="auth_email")
        password = st.text_input("Password", type="password", key="auth_pwd")
        name = st.text_input("Name (signup only)", key="auth_name")
        phone = st.text_input("Phone", key="auth_phone")
        db = next(get_db())
        if auth_mode == "Signup":
            if st.button("Create account"):
                if not email or not password:
                    st.warning("Please enter email and password.")
                elif get_user_by_email(db, email):
                    st.warning("Email already registered. Please login.")
                else:
                    u = create_user(db, email, password, name=name, phone=phone)
                    if u:
                        st.success("Account created. You are now logged in.")
                        st.session_state.current_user = u
                        st.experimental_rerun()
                    else:
                        st.error("Could not create account.")
        else:
            if st.button("Login"):
                u = get_user_by_email(db, email)
                if not u:
                    st.error("No user with that email. Signup first.")
                elif u.verify_password(password):
                    st.session_state.current_user = u
                    st.success("Logged in.")
                    st.experimental_rerun()
                else:
                    st.error("Incorrect password.")

if choice == "Home":
    st.title("LoanStream — Demo Loan App")
    st.markdown("""
    - Apply for loan
    - Upload KYC
    - Automated underwriting
    - Admin actions
    """)
    st.info("Use the sidebar to Signup or Login, then Apply.")

elif choice == "Apply":
    st.header("Apply for a Loan")
    if not st.session_state.current_user:
        st.warning("Please signup/login from the sidebar to apply.")
    else:
        with st.form("loan_form"):
            loan_amount = st.number_input("Loan amount (₹)", min_value=1000.0, value=50000.0, step=1000.0)
            tenure_months = st.selectbox("Tenure (months)", [6, 12, 24, 36, 48, 60], index=1)
            annual_rate = st.number_input("Annual interest rate (%)", min_value=0.1, value=12.0, step=0.1)
            income_monthly = st.number_input("Monthly income (₹)", min_value=0.0, value=30000.0, step=500.0)
            employment_type = st.selectbox("Employment type", ["Salaried", "Self-Employed", "Business", "Other"])
            st.write("EMI preview (approx): ₹", f"{calculate_emi(loan_amount, annual_rate, tenure_months):,.2f}")
            submitted = st.form_submit_button("Submit Application")
            if submitted:
                db = next(get_db())
                app = submit_application(db, st.session_state.current_user, loan_amount, tenure_months, annual_rate, income_monthly, employment_type)
                st.success("Application submitted. App ID: " + app.app_id)
                st.info("Go to Upload KYC to upload documents, then ask admin to run underwriting.")

elif choice == "Upload KYC":
    st.header("Upload KYC Documents")
    if not st.session_state.current_user:
        st.warning("Please login to upload KYC.")
    else:
        db = next(get_db())
        user = db.query(User).filter(User.id == st.session_state.current_user.id).first()
        apps = db.query(LoanApplication).filter(LoanApplication.user_id == user.id).order_by(LoanApplication.created_at.desc()).all()
        if not apps:
            st.info("No applications found. Start one from Apply.")
        else:
            sel = st.selectbox("Select application", [f"{a.app_id} - {a.status}" for a in apps])
            sel_app = next((a for a in apps if sel.startswith(a.app_id)), None)
            uploaded_file = st.file_uploader("Upload KYC (pdf, jpg, png).", accept_multiple_files=False)
            if uploaded_file and st.button("Save document"):
                k = save_kyc(db, sel_app, uploaded_file)
                st.success("Saved: " + k.filename)
            st.subheader("Existing documents")
            for a in apps:
                for d in a.kyc_docs:
                    st.write(f"{a.app_id} — {d.filename} — uploaded {d.uploaded_at}")
                    path = os.path.join(UPLOAD_DIR, d.filename)
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            st.download_button(label=f"Download {d.filename}", data=f.read(), file_name=d.filename)

elif choice == "Status":
    st.header("My Applications")
    if not st.session_state.current_user:
        st.warning("Please login to see your applications.")
    else:
        db = next(get_db())
        apps = db.query(LoanApplication).filter(LoanApplication.user_id == st.session_state.current_user.id).order_by(LoanApplication.created_at.desc()).all()
        if not apps:
            st.info("You have no applications.")
        else:
            for a in apps:
                st.markdown(f"**{a.app_id}** — Status: **{a.status}** — Amount: ₹{a.loan_amount:,.2f} — Tenure: {a.tenure_months} months")
                st.write("Credit score:", a.credit_score)
                st.write("DTI:", f"{(a.dti or 0):.2f}")
                st.write("Decision reason:", a.decision_reason or "N/A")
                if a.status == "Approved":
                    pdf_path = f"{a.app_id}_sanction.pdf"
                    user = db.query(User).filter(User.id == a.user_id).first()
                    generate_sanction_pdf(a, user, pdf_path)
                    with open(pdf_path, "rb") as f:
                        st.download_button("Download Sanction Letter (PDF)", data=f.read(), file_name=pdf_path)
                st.markdown("---")

elif choice == "Admin":
    st.header("Admin / Loan Officer")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")
    pw = st.text_input("Enter admin password", type="password")
    if pw != ADMIN_PASSWORD:
        st.warning("Enter admin password to continue.")
    else:
        db = next(get_db())
        st.success("Admin authenticated.")
        st.subheader("All Applications")
        apps = db.query(LoanApplication).order_by(LoanApplication.created_at.desc()).all()
        for a in apps:
            user = db.query(User).filter(User.id == a.user_id).first()
            cols = st.columns([2,1,1,1])
            cols[0].markdown(f"**{a.app_id}** — {user.email} — ₹{a.loan_amount:,.0f} — {a.tenure_months}m")
            cols[1].write(a.status)
            cols[2].write(a.credit_score or "-")
            cols[3].write(a.sanction_id or "-")
            with st.expander("Details / Actions"):
                st.write("Income (monthly):", a.income_monthly)
                st.write("Employment:", a.employment_type)
                for d in a.kyc_docs:
                    path = os.path.join(UPLOAD_DIR, d.filename)
                    st.write("KYC:", d.filename)
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            st.download_button(f"Download {d.filename}", data=f.read(), file_name=d.filename, key=f"dl-{d.id}")
                if a.status in ["Submitted", "Under Review"]:
                    if st.button(f"Run Underwriting - {a.app_id}", key=f"uw-{a.id}"):
                        a = run_underwriting(a, db)
                        st.experimental_rerun()
                if a.status == "Approved" and not a.sanction_id:
                    a.sanction_id = generate_id("SAN")
                    db.add(a)
                    db.commit()
                if st.button(f"Force Approve {a.app_id}", key=f"force-{a.id}"):
                    a.status = "Approved"
                    a.sanction_id = generate_id("SAN")
                    db.add(a)
                    db.commit()
                    st.success("Forced approval recorded.")
                if st.button(f"Force Reject {a.app_id}", key=f"fr-{a.id}"):
                    a.status = "Rejected"
                    a.decision_reason = "Manual rejection by admin."
                    db.add(a)
                    db.commit()
                    st.success("Forced rejection recorded.")
