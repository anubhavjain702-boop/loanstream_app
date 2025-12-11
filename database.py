# database.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
import bcrypt
from dotenv import load_dotenv
load_dotenv()

DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///data.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# ensure upload dir exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

engine = create_engine(DATABASE_URI, connect_args={"check_same_thread": False} if DATABASE_URI.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

def generate_id(prefix="ID"):
    now = datetime.utcnow().strftime("%y%m%d%H%M%S")
    return f"{prefix}{now}"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    def set_password(self, raw_password: str):
        self.hashed_password = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(raw_password.encode("utf-8"), self.hashed_password.encode("utf-8"))
        except Exception:
            return False

class LoanApplication(Base):
    __tablename__ = "loan_applications"
    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="Submitted")
    loan_amount = Column(Float, default=0.0)
    tenure_months = Column(Integer, default=12)
    annual_rate = Column(Float, default=12.0)
    income_monthly = Column(Float, nullable=True)
    employment_type = Column(String, nullable=True)
    credit_score = Column(Integer, nullable=True)
    dti = Column(Float, nullable=True)
    sanction_id = Column(String, nullable=True)
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", backref="applications")
    kyc_docs = relationship("KYC", backref="application", cascade="all, delete-orphan")

class KYC(Base):
    __tablename__ = "kyc"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("loan_applications.id"))
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    event = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

def init_db():
    Base.metadata.create_all(bind=engine)
