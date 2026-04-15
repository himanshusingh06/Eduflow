from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
import google.generativeai as genai
from fastapi import UploadFile, File
import PyPDF2
import io
import chromadb
from sentence_transformers import SentenceTransformer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pinecone import Pinecone, ServerlessSpec
from twilio.rest import Client as TwilioClient
import json
import httpx
import re
import asyncio
import html
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt, JWTError
import secrets
import hashlib
from motor.motor_asyncio import AsyncIOMotorClient
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Load environment variables


# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
security = HTTPBearer()
# Using SHA256 + salt for simplicity instead of bcrypt
import hashlib
JWT_SECRET = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_TIME = timedelta(days=7)
PASSWORD_SALT = "eduagent_salt_2024"
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://edumate.shiyaai.com/")
# AI Integration
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Pinecone Configuration
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

# Email Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
GOOGLE_SMTP_SERVER = os.environ.get("SMTP_SERVER", SMTP_SERVER)
GOOGLE_SMTP_PORT = int(os.environ.get("SMTP_PORT", str(SMTP_PORT)))
GOOGLE_SMTP_USER = os.environ.get("EMAIL_USER", EMAIL_USER or "")
GOOGLE_SMTP_PASSWORD = os.environ.get("EMAIL_PASSWORD", EMAIL_PASSWORD or "")
CONTACT_RECEIVER_EMAIL = os.environ.get("CONTACT_RECEIVER_EMAIL", GOOGLE_SMTP_USER or EMAIL_USER or "himanshuks062@gmail.com")

# WhatsApp Configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
WHATSAPP_WEBHOOK_URL = os.environ.get("WHATSAPP_WEBHOOK_URL")
# Replace with your real secret
RESET_SECRET_KEY = "SUPER_SECRET_KEY_FOR_PASSWORD_RESET"
ALGORITHM = "HS256"
RESET_TOKEN_EXPIRE_MINUTES = 15
# email verification config
EMAIL_SECRET_KEY = "your-very-secret-verification-key"
EMAIL_TOKEN_EXPIRE_MINUTES = 30  # verification link expires in 30 mins

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Create or connect to index
index_name = "eduagent-rag"
try:
    # Check if index exists, if not create it
    existing_indexes = [index.name for index in pc.list_indexes()]
    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=384,  # all-MiniLM-L6-v2 dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        logging.info("Pinecone index created successfully")
    
    pinecone_index = pc.Index(index_name)
    logging.info("Pinecone index initialized successfully")
except Exception as e:
    logging.error(f"Pinecone initialization error: {e}")
    pinecone_index = None

# Initialize sentence transformer for embeddings
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Twilio client
try:
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    else:
        twilio_client = None
        logging.warning("Twilio credentials not provided, WhatsApp features disabled")
except Exception as e:
    logging.error(f"Twilio initialization error: {e}")
    twilio_client = None

def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

# PhonePe Configuration
PHONEPE_BASE_URL = os.environ.get("PHONEPE_BASE_URL", "https://api-preprod.phonepe.com")
PHONEPE_OAUTH_ENDPOINT = os.environ.get("PHONEPE_OAUTH_ENDPOINT", "/apis/pg-sandbox/v1/oauth/token")
PHONEPE_PAY_ENDPOINT = os.environ.get("PHONEPE_PAY_ENDPOINT", "/apis/pg-sandbox/checkout/v2/pay")
PHONEPE_STATUS_ENDPOINT_TEMPLATE = os.environ.get(
    "PHONEPE_STATUS_ENDPOINT_TEMPLATE",
    "/apis/pg-sandbox/checkout/v2/order/{merchant_order_id}/status"
)
PHONEPE_CLIENT_ID = os.environ.get("PHONEPE_CLIENT_ID")
PHONEPE_CLIENT_SECRET = os.environ.get("PHONEPE_CLIENT_SECRET")
PHONEPE_CLIENT_VERSION = os.environ.get("PHONEPE_CLIENT_VERSION", "1")
PHONEPE_REDIRECT_BASE_URL = os.environ.get("PHONEPE_REDIRECT_BASE_URL", FRONTEND_URL)
PHONEPE_OAUTH_FALLBACK_ENDPOINT = os.environ.get("PHONEPE_OAUTH_FALLBACK_ENDPOINT", "/apis/identity-manager/v1/oauth/token")

# Subscription/Trial configuration
SUBSCRIPTION_TRIAL_DAYS = _env_int("SUBSCRIPTION_TRIAL_DAYS", 7)
SUBSCRIPTION_MONTHLY_PLAN_AMOUNT = _env_int("SUBSCRIPTION_MONTHLY_PLAN_AMOUNT", 19900)
SUBSCRIPTION_YEARLY_PLAN_AMOUNT = _env_int("SUBSCRIPTION_YEARLY_PLAN_AMOUNT", 179900)
SUBSCRIPTION_MONTHLY_DURATION_DAYS = _env_int("SUBSCRIPTION_MONTHLY_DURATION_DAYS", 30)
SUBSCRIPTION_YEARLY_DURATION_DAYS = _env_int("SUBSCRIPTION_YEARLY_DURATION_DAYS", 365)

# Internal Admin bootstrap (not public signup)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@eduflow.local")
ADMIN_NAME = os.environ.get("ADMIN_NAME", "Platform Admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe@123")

CALLBACK_BASE_URL = PHONEPE_REDIRECT_BASE_URL

# Create the main app
app = FastAPI(title="EduAgent - AI Powered Educational Platform",docs_url="/api/docs",redoc_url="/api/redoc",openapi_url="/api/openapi.json")
# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ============= MODELS =============

# User Roles Constants
class UserRoles:
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"
    ADMIN = "admin"

class UserBase(BaseModel):
    email: str
    name: str
    role: str  # student, teacher, parent, admin
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = False
    is_active: bool = True
    is_blocked: bool = False
    blocked_reason: Optional[str] = None
    blocked_at: Optional[datetime] = None
    blocked_by: Optional[str] = None
    trial_start_at: Optional[datetime] = None
    trial_end_at: Optional[datetime] = None
    student_access: Optional[Dict[str, Any]] = None
    parent_id: Optional[str] = None  # For students linked to parents
    students: List[str] = []  # For parents linked to students
    classes: List[str] = []  # For teachers and students

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

# Study Content Models
class StudyContent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    subject: str
    grade_level: str
    content: str
    ai_generated: bool = True
    created_by: str  # teacher_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []

class StudyContentCreate(BaseModel):
    title: str
    subject: str
    grade_level: str
    topic: str  # For AI generation
    tags: List[str] = []

# Quiz Models
class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int
    explanation: str

class Quiz(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    subject: str
    grade_level: str
    questions: List[QuizQuestion]
    created_by: str  # teacher_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    time_limit: int = 30  # minutes
    total_marks: int

class QuizCreate(BaseModel):
    title: str
    subject: str
    grade_level: str
    topic: str
    num_questions: int = 10
    difficulty: str = "medium"  # easy, medium, hard

class QuizAttempt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quiz_id: str
    student_id: str
    answers: Dict[str, int]  # question_index: selected_option
    score: int
    total_marks: int
    percentage: float
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    time_taken: int  # minutes

# Q&A Models
class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    question: str
    subject: str
    answer: Optional[str] = None
    answered_by: str = "AI"  # AI or teacher_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    answered_at: Optional[datetime] = None

class QuestionCreate(BaseModel):
    question: str
    subject: str

# Progress Models
class StudentProgress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    subject: str
    total_quizzes: int = 0
    average_score: float = 0.0
    total_questions_asked: int = 0
    study_sessions: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    strengths: List[str] = []
    weaknesses: List[str] = []

# Chat Models
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: str = "text"  # text, whatsapp
    is_read: bool = False

class ChatMessageCreate(BaseModel):
    receiver_id: str
    message: str

# Payment Models
class SubscriptionPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    amount: int  # Amount in paise
    billing_cycle: str  # monthly, yearly
    duration_days: int
    features: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentRequest(BaseModel):
    amount: int  # Amount in paise
    description: str
    payment_type: str = "one_time"  # one_time, subscription

class SubscriptionRequest(BaseModel):
    plan_id: str

class PaymentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str
    subscription_id: Optional[str] = None
    student_id: str
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    billing_cycle: Optional[str] = None
    amount: int
    payment_type: str  # one_time, subscription, renewal
    status: str  # INITIATED, PENDING, SUCCESS, FAILED
    description: str
    provider: str = "phonepe"
    merchant_order_id: Optional[str] = None
    provider_order_id: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    paid_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    plan_id: str
    plan_name: str
    billing_cycle: str
    status: str  # ACTIVE, INACTIVE, EXPIRED, PENDING, CANCELED
    start_date: datetime
    end_date: datetime
    amount: int
    next_billing_date: Optional[datetime] = None
    auto_renewal: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_payment_date: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    canceled_by: Optional[str] = None
    restored_at: Optional[datetime] = None
    restored_by: Optional[str] = None
    restored_from_subscription_id: Optional[str] = None
    restored_from_plan_id: Optional[str] = None
    restored_from_plan_name: Optional[str] = None

class AdminUserAction(BaseModel):
    reason: Optional[str] = None

class AdminRestoreSubscriptionRequest(BaseModel):
    restore_option: str = "previous"  # previous, monthly, yearly
    reason: Optional[str] = None

# Personalized Learning Models
class LearningPath(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    subject: str
    current_level: str  # beginner, intermediate, advanced
    recommended_topics: List[str] = []
    completed_topics: List[str] = []
    weak_areas: List[str] = []
    strong_areas: List[str] = []
    next_recommendations: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LearningInsight(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    insight_type: str  # performance, recommendation, achievement
    title: str
    description: str
    priority: str  # high, medium, low
    action_required: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# File Upload Models
class StudyMaterial(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    uploaded_by: str  # teacher_id
    subject: str
    grade_level: str
    description: str
    file_path: str
    is_processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StudyMaterialUpload(BaseModel):
    subject: str
    grade_level: str
    description: str

# RAG and Notes Models
class RAGDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    material_id: str
    content: str
    page_number: int
    embedding_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StudentNote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    title: str
    content: str
    subject: str
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NoteCreateRequest(BaseModel):
    title: str
    content: str
    subject: str
    tags: List[str] = []

class NoteSummaryRequest(BaseModel):
    note_content: str
    summary_type: str = "brief"  # brief, detailed, key_points

class RAGQueryRequest(BaseModel):
    question: str
    subject: Optional[str] = None
    grade_level: Optional[str] = None

# Quiz Analysis Models
class QuizAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    quiz_id: str
    attempt_id: str
    analysis_data: Dict[str, Any] = {}
    insights: List[str] = []
    recommendations: List[str] = []
    performance_trend: str  # improving, declining, stable
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Dynamic Quiz Models
class DynamicQuizRequest(BaseModel):
    subject: str
    topic: str
    difficulty: str  # easy, medium, hard
    num_questions: int = Field(ge=5, le=10)  # Between 5 and 10 questions
    grade_level: Optional[str] = "Grade 8"

class QuizEvaluation(BaseModel):
    student_id: str
    quiz_data: Dict[str, Any]
    student_answers: Dict[str, Any]
    score: int
    total_questions: int
    percentage: float
    evaluation_report: str
    recommendations: List[str]
    strengths: List[str]
    weaknesses: List[str]

# Email Models
class EmailReport(BaseModel):
    recipient_email: str
    student_name: str
    quiz_title: str
    score: int
    total_questions: int
    percentage: float
    evaluation_report: str
    recommendations: List[str]

class ContactFormRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    role: str = Field(default="student", min_length=2, max_length=50)
    institution: Optional[str] = Field(default=None, max_length=160)
    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=3, max_length=4000)

# Student PDF Upload Model  
class StudentPDFUpload(BaseModel):
    student_id: str
    filename: str
    original_filename: str
    file_size: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

# WhatsApp Models
class WhatsAppMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: str
    message_text: str
    student_id: Optional[str] = None
    message_type: str  # incoming, outgoing
    processed: bool = False
    response_sent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WhatsAppUser(BaseModel):
    phone_number: str
    student_id: Optional[str] = None
    name: Optional[str] = None
    registered: bool = False
    last_activity: datetime = Field(default_factory=datetime.utcnow)



# ======== Schemas ========
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# ======== Utils ========
def generate_reset_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, RESET_SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, RESET_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


SUBSCRIPTION_PLAN_CATALOG = {
    "monthly_199": {
        "id": "monthly_199",
        "name": "Monthly Student Plan",
        "description": "Full app access billed every month",
        "amount": SUBSCRIPTION_MONTHLY_PLAN_AMOUNT,
        "billing_cycle": "monthly",
        "duration_days": SUBSCRIPTION_MONTHLY_DURATION_DAYS,
        "price_display": f"Rs {SUBSCRIPTION_MONTHLY_PLAN_AMOUNT / 100:.0f}/month",
        "features": [
            "Unlimited quizzes and practice",
            "AI tutor and doubt support",
            "Personalized learning path",
            "Notes and PDF assistant",
        ],
    },
    "yearly_1799": {
        "id": "yearly_1799",
        "name": "Yearly Student Plan",
        "description": "Best value annual access",
        "amount": SUBSCRIPTION_YEARLY_PLAN_AMOUNT,
        "billing_cycle": "yearly",
        "duration_days": SUBSCRIPTION_YEARLY_DURATION_DAYS,
        "price_display": f"Rs {SUBSCRIPTION_YEARLY_PLAN_AMOUNT / 100:.0f}/year",
        "features": [
            "Everything in monthly plan",
            "Priority support",
            "Lower effective monthly cost",
            "Single yearly payment",
        ],
    },
}

STUDENT_FREE_ACCESS_PREFIXES = [
    "/api/auth/me",
    "/api/dashboard/student",
    "/api/subscription-plans",
    "/api/my-subscription",
    "/api/create-subscription",
    "/api/payment-status/",
    "/api/payments/phonepe/",
    "/api/student/profile",
    "/api/payment-success",
    "/api/payment-failure",
]


def get_subscription_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    return SUBSCRIPTION_PLAN_CATALOG.get(plan_id)


def list_subscription_plans() -> List[Dict[str, Any]]:
    return list(SUBSCRIPTION_PLAN_CATALOG.values())


def calculate_subscription_dates(plan_id: str, from_date: Optional[datetime] = None) -> Dict[str, datetime]:
    plan = get_subscription_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    start_date = from_date or datetime.utcnow()
    end_date = start_date + timedelta(days=plan["duration_days"])
    return {"start_date": start_date, "end_date": end_date, "next_billing_date": end_date}


def normalize_phonepe_state(raw_state: Optional[str]) -> str:
    state = (raw_state or "").upper().strip()
    if state in {"COMPLETED", "SUCCESS", "CAPTURED", "PAYMENT_SUCCESS"}:
        return "SUCCESS"
    if state in {"PENDING", "CREATED", "INITIATED", "PAYMENT_PENDING"}:
        return "PENDING"
    if state in {"FAILED", "FAILURE", "DECLINED", "EXPIRED", "CANCELLED"}:
        return "FAILED"
    return "UNKNOWN"


def _build_phonepe_url(endpoint: str) -> str:
    return f"{PHONEPE_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

PHONEPE_TOKEN_CACHE: Dict[str, Any] = {
    "token": None,
    "expires_at": datetime.utcnow(),
}


async def get_phonepe_access_token() -> str:
    if not PHONEPE_CLIENT_ID or not PHONEPE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="PhonePe credentials are not configured")

    if PHONEPE_TOKEN_CACHE["token"] and PHONEPE_TOKEN_CACHE["expires_at"] > datetime.utcnow():
        return PHONEPE_TOKEN_CACHE["token"]

    payload = {
        "client_id": PHONEPE_CLIENT_ID,
        "client_secret": PHONEPE_CLIENT_SECRET,
        "client_version": PHONEPE_CLIENT_VERSION,
        "grant_type": "client_credentials",
    }

    endpoints_to_try = []
    for endpoint in [PHONEPE_OAUTH_ENDPOINT, PHONEPE_OAUTH_FALLBACK_ENDPOINT]:
        if endpoint and endpoint not in endpoints_to_try:
            endpoints_to_try.append(endpoint)

    errors: List[str] = []
    async with httpx.AsyncClient(timeout=20.0) as client_http:
        for endpoint in endpoints_to_try:
            token_url = _build_phonepe_url(endpoint)
            response = await client_http.post(
                token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code >= 400:
                errors.append(f"{endpoint}: {response.status_code} {response.text}")
                continue

            try:
                body = response.json()
            except Exception:
                errors.append(f"{endpoint}: invalid JSON response")
                continue

            token = (
                body.get("access_token")
                or body.get("accessToken")
                or body.get("data", {}).get("accessToken")
                or body.get("data", {}).get("access_token")
            )
            expires_in = (
                body.get("expires_in")
                or body.get("expiresIn")
                or body.get("data", {}).get("expiresIn")
                or body.get("data", {}).get("expires_in")
                or 600
            )
            try:
                expires_in = int(expires_in)
            except Exception:
                expires_in = 600

            if token:
                PHONEPE_TOKEN_CACHE["token"] = token
                PHONEPE_TOKEN_CACHE["expires_at"] = datetime.utcnow() + timedelta(seconds=max(60, expires_in - 60))
                return token

            errors.append(f"{endpoint}: token missing in response")

    raise HTTPException(
        status_code=502,
        detail=f"PhonePe token request failed. Tried endpoints: {' | '.join(errors) if errors else 'none'}",
    )


async def call_phonepe_api(method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    access_token = await get_phonepe_access_token()
    headers = {
        "Authorization": f"O-Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=25.0) as client_http:
        response = await client_http.request(
            method=method,
            url=_build_phonepe_url(endpoint),
            json=payload,
            headers=headers,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PhonePe API failed: {response.text}")

    try:
        return response.json()
    except Exception:
        return {"raw": response.text}


async def create_phonepe_checkout_order(
    transaction_id: str,
    student_id: str,
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    redirect_url = (
        f"{PHONEPE_REDIRECT_BASE_URL.rstrip('/')}/"
        f"?payment_return=1&transaction_id={transaction_id}"
    )
    message = f"{plan['name']} subscription purchase"
    amount = plan["amount"]

    request_variants = [
        {
            "merchantOrderId": transaction_id,
            "amount": amount,
            "expireAfter": 1200,
            "metaInfo": {"udf1": student_id, "udf2": plan["id"]},
            "paymentFlow": {
                "type": "PG_CHECKOUT",
                "message": message,
                "merchantUrls": {"redirectUrl": redirect_url},
            },
        },
        {
            "merchantOrderId": transaction_id,
            "amount": amount,
            "redirectUrl": redirect_url,
            "message": message,
        },
    ]

    last_error: Optional[HTTPException] = None
    for payload in request_variants:
        try:
            response = await call_phonepe_api("POST", PHONEPE_PAY_ENDPOINT, payload=payload)
            data = response.get("data", response)
            payment_redirect_url = (
                data.get("redirectUrl")
                or data.get("paymentUrl")
                or data.get("redirect_url")
                or data.get("instrumentResponse", {}).get("redirectInfo", {}).get("url")
            )
            provider_order_id = data.get("orderId") or data.get("merchantOrderId") or transaction_id
            if payment_redirect_url:
                return {
                    "provider_order_id": provider_order_id,
                    "redirect_url": payment_redirect_url,
                    "provider_response": response,
                }
        except HTTPException as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error
    raise HTTPException(status_code=502, detail="PhonePe checkout response missing redirect URL")


async def fetch_phonepe_order_status(merchant_order_id: str) -> Dict[str, Any]:
    status_endpoint = PHONEPE_STATUS_ENDPOINT_TEMPLATE.format(merchant_order_id=merchant_order_id)
    response = await call_phonepe_api("GET", status_endpoint)
    data = response.get("data", response)
    raw_state = (
        data.get("state")
        or data.get("status")
        or data.get("paymentDetails", {}).get("state")
        or data.get("paymentDetails", {}).get("status")
    )
    return {"raw_state": raw_state, "normalized_state": normalize_phonepe_state(raw_state), "response": response}


async def expire_student_subscriptions(student_id: str) -> None:
    now = datetime.utcnow()
    await db.subscriptions.update_many(
        {
            "student_id": student_id,
            "status": {"$in": ["ACTIVE", "PENDING"]},
            "end_date": {"$lt": now},
        },
        {"$set": {"status": "EXPIRED", "updated_at": now}},
    )


async def get_latest_student_subscription(student_id: str) -> Optional[Dict[str, Any]]:
    subscriptions = await db.subscriptions.find({"student_id": student_id}).sort("created_at", -1).to_list(1)
    return subscriptions[0] if subscriptions else None


async def get_active_student_subscription(student_id: str) -> Optional[Dict[str, Any]]:
    now = datetime.utcnow()
    subs = await db.subscriptions.find(
        {"student_id": student_id, "status": "ACTIVE", "end_date": {"$gt": now}}
    ).sort("updated_at", -1).to_list(1)
    return subs[0] if subs else None


def clean_document(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    return {k: v for k, v in doc.items() if k != "_id"}


def extract_subscription_snapshot(subscription: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not subscription:
        return None
    return {
        "subscription_id": subscription.get("id"),
        "plan_id": subscription.get("plan_id"),
        "plan_name": subscription.get("plan_name"),
        "billing_cycle": subscription.get("billing_cycle"),
        "amount": subscription.get("amount"),
        "status": subscription.get("status"),
        "start_date": subscription.get("start_date"),
        "end_date": subscription.get("end_date"),
        "next_billing_date": subscription.get("next_billing_date"),
        "updated_at": subscription.get("updated_at"),
    }


def derive_student_status(
    user_doc: Dict[str, Any],
    active_subscription: Optional[Dict[str, Any]],
    latest_subscription: Optional[Dict[str, Any]],
    now: datetime,
) -> Dict[str, Any]:
    trial_end = user_doc.get("trial_end_at")
    trial_active = bool(trial_end and trial_end > now)
    trial_days_remaining = 0
    if trial_end and trial_end > now:
        trial_days_remaining = max(0, (trial_end.date() - now.date()).days)

    is_blocked = bool(user_doc.get("is_blocked"))
    latest_billing_cycle = (latest_subscription or {}).get("billing_cycle")
    had_paid_plan = latest_billing_cycle in {"monthly", "yearly"}

    if is_blocked:
        status_label = "BLOCKED"
        lifecycle_status = "BLOCKED"
        message = user_doc.get("blocked_reason") or "Your account is blocked by admin."
        access_allowed = False
    elif active_subscription:
        billing_cycle = (active_subscription.get("billing_cycle") or "").lower()
        lifecycle_status = "YEARLY_SUBSCRIPTION" if billing_cycle == "yearly" else "MONTHLY_SUBSCRIPTION"
        status_label = "ACTIVE_SUBSCRIPTION"
        message = "Your paid subscription is active."
        access_allowed = True
    elif trial_active:
        lifecycle_status = "FREE_TRIAL_ACTIVE" if had_paid_plan else "FREE_TIER"
        status_label = "TRIAL_ACTIVE"
        message = f"Free trial active for {trial_days_remaining} day(s)."
        access_allowed = True
    else:
        lifecycle_status = "FREE_TRIAL_ENDED"
        status_label = "PAYMENT_REQUIRED"
        message = "Your free trial ended. Please subscribe to continue."
        access_allowed = False

    return {
        "status": status_label,
        "lifecycle_status": lifecycle_status,
        "message": message,
        "access_allowed": access_allowed,
        "trial_end_at": trial_end,
        "trial_days_remaining": trial_days_remaining,
        "is_blocked": is_blocked,
    }


async def sync_student_status_state(
    user_doc: Dict[str, Any],
    lifecycle_status: str,
    access_status: str,
    access_allowed: bool,
    now: datetime,
) -> None:
    should_update = (
        user_doc.get("student_status") != lifecycle_status
        or user_doc.get("student_access_status") != access_status
        or user_doc.get("student_access_allowed") != access_allowed
    )
    if not should_update:
        return

    await db.users.update_one(
        {"id": user_doc.get("id")},
        {
            "$set": {
                "student_status": lifecycle_status,
                "student_access_status": access_status,
                "student_access_allowed": access_allowed,
                "student_status_updated_at": now,
            }
        },
    )


async def store_previous_subscription_snapshot(
    student_id: str,
    subscription: Optional[Dict[str, Any]],
    source: str,
    action_by: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    snapshot = extract_subscription_snapshot(subscription)
    if not snapshot:
        return

    now = datetime.utcnow()
    snapshot.update(
        {
            "snapshot_source": source,
            "snapshot_reason": reason,
            "snapshot_by": action_by,
            "snapshot_at": now,
        }
    )
    await db.users.update_one(
        {"id": student_id},
        {"$set": {"previous_subscription": snapshot, "updated_at": now}},
    )


async def get_subscription_conflict(student_id: str) -> Optional[Dict[str, Any]]:
    now = datetime.utcnow()
    await expire_student_subscriptions(student_id)
    candidates = await db.subscriptions.find(
        {"student_id": student_id, "status": {"$in": ["ACTIVE", "PENDING"]}}
    ).sort("updated_at", -1).to_list(20)

    for subscription in candidates:
        if subscription.get("status") == "PENDING":
            return subscription
        if subscription.get("status") == "ACTIVE" and subscription.get("end_date") and subscription["end_date"] > now:
            return subscription
    return None


async def build_student_access_context(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    student_id = user_doc.get("id")
    await expire_student_subscriptions(student_id)

    trial_end = user_doc.get("trial_end_at")
    if not trial_end and user_doc.get("created_at"):
        trial_end = user_doc["created_at"] + timedelta(days=SUBSCRIPTION_TRIAL_DAYS)
        await db.users.update_one({"id": student_id}, {"$set": {"trial_end_at": trial_end}})

    active_subscription = await get_active_student_subscription(student_id)
    latest_subscription = await get_latest_student_subscription(student_id)
    status_info = derive_student_status(user_doc, active_subscription, latest_subscription, now)
    await sync_student_status_state(
        user_doc,
        lifecycle_status=status_info["lifecycle_status"],
        access_status=status_info["status"],
        access_allowed=status_info["access_allowed"],
        now=now,
    )

    clean_subscription = clean_document(active_subscription) or clean_document(latest_subscription)
    previous_subscription = user_doc.get("previous_subscription")
    if not previous_subscription and latest_subscription and latest_subscription.get("status") in {"CANCELED", "EXPIRED", "INACTIVE"}:
        previous_subscription = extract_subscription_snapshot(latest_subscription)

    return {
        "status": status_info["status"],
        "lifecycle_status": status_info["lifecycle_status"],
        "message": status_info["message"],
        "access_allowed": status_info["access_allowed"],
        "trial_end_at": status_info["trial_end_at"],
        "trial_days_remaining": status_info["trial_days_remaining"],
        "has_active_subscription": bool(active_subscription),
        "subscription": clean_subscription,
        "previous_subscription": previous_subscription,
        "next_billing_date": (
            (active_subscription or latest_subscription or {}).get("next_billing_date")
            or (active_subscription or latest_subscription or {}).get("end_date")
        ),
        "is_blocked": status_info["is_blocked"],
    }


def student_access_allowed_for_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in STUDENT_FREE_ACCESS_PREFIXES)


async def ensure_admin_user_exists() -> None:
    admin_doc = await db.users.find_one({"email": ADMIN_EMAIL})
    now = datetime.utcnow()

    if not admin_doc:
        admin_user = User(
            id=str(uuid.uuid4()),
            email=ADMIN_EMAIL,
            name=ADMIN_NAME,
            role=UserRoles.ADMIN,
            is_verified=True,
            is_active=True,
            created_at=now,
        ).dict()
        admin_user["password"] = hash_password(ADMIN_PASSWORD)
        await db.users.insert_one(admin_user)
        logging.info("Internal admin account bootstrapped")
        return

    update_payload = {
        "role": UserRoles.ADMIN,
        "is_verified": True,
        "is_active": True,
        "updated_at": now,
    }
    if not admin_doc.get("password"):
        update_payload["password"] = hash_password(ADMIN_PASSWORD)
    await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": update_payload})


def ensure_admin_role(current_user: User) -> None:
    if current_user.role != UserRoles.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")


async def finalize_payment_status(
    transaction_id: str,
    current_user: Optional[User] = None,
) -> Dict[str, Any]:
    payment_record = await db.payments.find_one({"transaction_id": transaction_id})
    if not payment_record:
        raise HTTPException(status_code=404, detail="Payment not found")

    if current_user and current_user.role == UserRoles.STUDENT and payment_record.get("student_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    merchant_order_id = payment_record.get("merchant_order_id") or transaction_id
    status_response = await fetch_phonepe_order_status(merchant_order_id)
    normalized_state = status_response["normalized_state"]
    now = datetime.utcnow()

    subscription_id = payment_record.get("subscription_id") or transaction_id
    subscription = await db.subscriptions.find_one({"id": subscription_id})
    if payment_record.get("payment_type") == "subscription" and not subscription:
        raise HTTPException(status_code=409, detail="Subscription record missing for payment")
    if (
        payment_record.get("payment_type") == "subscription"
        and subscription
        and subscription.get("student_id") != payment_record.get("student_id")
    ):
        raise HTTPException(status_code=409, detail="Payment and subscription owner mismatch")

    payment_update: Dict[str, Any] = {
        "provider_response": status_response["response"],
        "updated_at": now,
    }

    if normalized_state == "SUCCESS":
        payment_update.update({"status": "SUCCESS", "paid_at": now, "failure_reason": None})
    elif normalized_state == "FAILED":
        payment_update.update({"status": "FAILED", "failure_reason": "Payment failed at provider"})
    else:
        payment_update["status"] = "PENDING"

    await db.payments.update_one({"transaction_id": transaction_id}, {"$set": payment_update})

    subscription_result = None
    if payment_record.get("payment_type") == "subscription":
        if normalized_state == "SUCCESS":
            if subscription and subscription.get("status") == "CANCELED":
                raise HTTPException(status_code=409, detail="Cannot activate a canceled subscription")

            if subscription:
                await db.subscriptions.update_many(
                    {
                        "student_id": payment_record["student_id"],
                        "status": "ACTIVE",
                        "id": {"$ne": subscription_id},
                    },
                    {"$set": {"status": "INACTIVE", "updated_at": now}},
                )

                await db.subscriptions.update_one(
                    {"id": subscription_id},
                    {
                        "$set": {
                            "status": "ACTIVE",
                            "last_payment_date": now,
                            "updated_at": now,
                            "next_billing_date": subscription.get("end_date"),
                        }
                    },
                )
                subscription_result = await db.subscriptions.find_one({"id": subscription_id})
        elif normalized_state == "FAILED":
            if subscription and subscription.get("status") == "PENDING":
                await db.subscriptions.update_one(
                    {"id": subscription_id},
                    {"$set": {"status": "INACTIVE", "updated_at": now, "failure_reason": "Payment failed"}},
                )
                subscription_result = await db.subscriptions.find_one({"id": subscription_id})
        else:
            subscription_result = subscription

    return {
        "transaction_id": transaction_id,
        "payment_status": payment_update["status"],
        "gateway_status": status_response["raw_state"],
        "subscription": {k: v for k, v in subscription_result.items() if k != "_id"} if subscription_result else None,
    }



async def send_reset_email(email: str, reset_link: str):
    """Send a password reset email via Gmail SMTP."""
    try:
        # Email content
        subject = "Password Reset Request"
        body = f"""
        <html>
            <body>
                <p>Hi,</p>
                <p>We received a request to reset your password. Click the link below to reset it:</p>
                 <a href="{reset_link}"
               style="background-color:#4CAF50;color:white;
                      padding:10px 15px;text-decoration:none;
                      border-radius:5px;">Reset Link</a>
                <p>This link will expire in 15 minutes.</p>
                <br>
                <p>If you didn't request this, please ignore this email.</p>
                <p>— Edumate Team</p>
            </body>
        </html>
        """

        # MIME setup
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure connection
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, email, message.as_string())

        print(f"✅ Password reset email sent to {email}")

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        raise e

# ======== Routes ========

async def send_contact_form_email(contact_form: ContactFormRequest) -> None:
    """Send a landing page contact request through Google SMTP."""
    smtp_user = GOOGLE_SMTP_USER or EMAIL_USER
    smtp_password = GOOGLE_SMTP_PASSWORD or EMAIL_PASSWORD
    smtp_server = GOOGLE_SMTP_SERVER or SMTP_SERVER
    smtp_port = GOOGLE_SMTP_PORT or SMTP_PORT
    recipient_email = CONTACT_RECEIVER_EMAIL or smtp_user

    if not smtp_user or not smtp_password or not recipient_email:
        logging.error("Contact form email configuration is incomplete")
        raise HTTPException(
            status_code=500,
            detail="Support email is not configured right now. Please try again later.",
        )

    role_label = contact_form.role.replace("_", " ").title()
    institution = contact_form.institution or "Not provided"
    phone = contact_form.phone or "Not provided"
    safe_name = html.escape(contact_form.full_name)
    safe_email = html.escape(contact_form.email)
    safe_phone = html.escape(phone)
    safe_role = html.escape(role_label)
    safe_institution = html.escape(institution)
    safe_subject = html.escape(contact_form.subject)
    safe_message = html.escape(contact_form.message)

    subject = f"[EduMate Contact] {contact_form.subject} - {role_label}"
    plain_body = (
        "New EduMate landing page inquiry\n\n"
        f"Name: {contact_form.full_name}\n"
        f"Email: {contact_form.email}\n"
        f"Phone: {phone}\n"
        f"Role: {role_label}\n"
        f"Institution: {institution}\n"
        f"Subject: {contact_form.subject}\n\n"
        "Message:\n"
        f"{contact_form.message}\n"
    )
    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f8fafc;color:#0f172a;padding:24px;">
        <div style="max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #d1fae5;border-radius:18px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#10b981,#0f766e);padding:24px;color:#ffffff;">
            <h2 style="margin:0 0 6px 0;">New EduMate Contact Request</h2>
            <p style="margin:0;opacity:0.92;">A visitor submitted the landing page contact form.</p>
          </div>
          <div style="padding:24px;">
            <p style="margin:0 0 16px 0;"><strong>Name:</strong> {safe_name}</p>
            <p style="margin:0 0 16px 0;"><strong>Email:</strong> {safe_email}</p>
            <p style="margin:0 0 16px 0;"><strong>Phone:</strong> {safe_phone}</p>
            <p style="margin:0 0 16px 0;"><strong>Role:</strong> {safe_role}</p>
            <p style="margin:0 0 16px 0;"><strong>Institution:</strong> {safe_institution}</p>
            <p style="margin:0 0 16px 0;"><strong>Subject:</strong> {safe_subject}</p>
            <div style="margin-top:20px;padding:18px;background:#ecfdf5;border-radius:14px;border:1px solid #a7f3d0;">
              <p style="margin:0 0 8px 0;font-weight:700;">Message</p>
              <p style="margin:0;line-height:1.7;white-space:pre-wrap;">{safe_message}</p>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = smtp_user
    message["To"] = recipient_email
    message["Reply-To"] = contact_form.email
    message.attach(MIMEText(plain_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, message.as_string())
        logging.info("Contact form email sent successfully for %s", contact_form.email)
    except Exception as exc:
        logging.error("Failed to send contact form email: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="We could not send your message right now. Please try again in a little while.",
        ) from exc


def _format_contact_validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    def _friendly_error_message(field_name: str, error: dict[str, Any]) -> str:
        error_type = str(error.get("type", ""))
        raw_message = str(error.get("msg", "Invalid value."))
        context = error.get("ctx") or {}

        if "email" in field_name or "email" in error_type or "email" in raw_message.lower():
            return "Please enter a valid email address."

        if error_type in {"string_too_short", "too_short"}:
            min_length = context.get("min_length")
            if isinstance(min_length, int):
                return f"Please enter at least {min_length} characters."
            return "This value is too short."

        if error_type in {"string_too_long", "too_long"}:
            max_length = context.get("max_length")
            if isinstance(max_length, int):
                return f"Please keep this under {max_length} characters."
            return "This value is too long."

        if error_type in {"missing", "string_type"}:
            return "This field is required."

        return raw_message

    formatted_errors = []
    for error in exc.errors():
        loc = error.get("loc", ())
        field_name = next((str(part) for part in reversed(loc) if part != "body"), "form")
        friendly_message = _friendly_error_message(field_name, error)
        formatted_errors.append(
            {
                "field": field_name,
                "message": friendly_message,
            }
        )
    return formatted_errors


@api_router.post("/contact")
async def submit_contact_form(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "We could not read the contact form submission. Please refresh the page and try again.",
                "errors": [],
            },
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Please fill out the contact form correctly and try again.",
                "errors": [{"field": "form", "message": "Invalid contact form payload."}],
            },
        )

    normalized_payload = {
        "full_name": str(payload.get("full_name", "")).strip(),
        "email": str(payload.get("email", "")).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "role": str(payload.get("role", "student")).strip().lower() or "student",
        "institution": str(payload.get("institution", "")).strip(),
        "subject": str(payload.get("subject", "")).strip(),
        "message": str(payload.get("message", "")).strip(),
    }

    try:
        contact_form = ContactFormRequest.model_validate(normalized_payload)
    except ValidationError as exc:
        errors = _format_contact_validation_errors(exc)
        return JSONResponse(
            status_code=422,
            content={
                "detail": errors[0]["message"] if errors else "Please review the contact form fields and try again.",
                "errors": errors,
            },
        )

    await send_contact_form_email(contact_form)
    return {
        "message": "Thank you for reaching out. Your message has been sent to our support team.",
    }

@api_router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """Request password reset link"""
    user = await db.users.find_one({"email": data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )
    
    # Generate reset token
    token = generate_reset_token(data.email)
    reset_link = f"{FRONTEND_URL}verify-reset-token/{token}"

    # Store token in user doc (optional)
    await db.users.update_one(
        {"email": data.email},
        {"$set": {"reset_token": token, "reset_requested_at": datetime.utcnow()}}
    )

    # Send reset email
    try:
        await send_reset_email(data.email, reset_link)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")
    
    return {"message": "Password reset link has been sent to your email"}


@api_router.get("/auth/verify-reset-token/{token}")
async def verify_token(token: str):
    """Verify if reset token is valid"""
    email = verify_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"message": "Token valid", "email": email}


@api_router.post("/auth/reset-password")
async def reset_password(data: ResetPasswordRequest):
    """Reset the password using the token"""
    email = verify_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Hash the new password
    new_hashed = hash_password(data.new_password)

    # Update in DB
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"password": new_hashed}, "$unset": {"reset_token": ""}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Unable to reset password")
    
    return {"message": "Password has been reset successfully"}
# ============= UTILITY FUNCTIONS =============



def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Verify password by hashing the plain password and comparing
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + JWT_EXPIRATION_TIME
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    user_model = User(**{k: v for k, v in user.items() if k != "password"})

    if user_model.role == UserRoles.STUDENT:
        student_access = await build_student_access_context(user)
        user_model.student_access = student_access

        if not student_access.get("access_allowed", True) and not student_access_allowed_for_path(request.url.path):
            raise HTTPException(status_code=403, detail=student_access.get("message"))

    if user_model.is_blocked and request.url.path != "/api/auth/me":
        raise HTTPException(status_code=403, detail=user_model.blocked_reason or "Your account is blocked")

    return user_model

# ============= AI FUNCTIONS =============

async def generate_study_content(topic: str, subject: str, grade_level: str) -> str:
    """Generate personalized study content using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""You are an expert educator creating study content for {grade_level} students in {subject}.

Create comprehensive study content about '{topic}' that includes:
1. Clear introduction and learning objectives
2. Key concepts explained in simple terms
3. Real-world examples and applications
4. Important formulas or facts (if applicable)
5. Practice questions or activities

Make it engaging, age-appropriate, and well-structured for {grade_level} level understanding."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"AI content generation error: {e}")
        return f"Study content for {topic}: This is a comprehensive overview of {topic} in {subject}. [AI generation failed, please try again]"

async def generate_quiz(topic: str, subject: str, grade_level: str, num_questions: int = 10, difficulty: str = "medium") -> List[QuizQuestion]:
    """Generate quiz questions using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""Generate {num_questions} multiple choice questions about '{topic}' for {grade_level} students in {subject}.
Difficulty level: {difficulty}

Format your response as a JSON array with each question having:
- "question": the question text
- "options": array of 4 answer choices
- "correct_answer": index (0-3) of the correct answer
- "explanation": brief explanation of the correct answer

Example format:
[
  {{
    "question": "What is photosynthesis?",
    "options": ["A process in animals", "A process in plants", "A chemical reaction", "All of the above"],
    "correct_answer": 1,
    "explanation": "Photosynthesis is the process by which plants convert sunlight into energy."
  }}
]

Generate {num_questions} questions now:"""

        response = model.generate_content(prompt)
        
        # Parse AI response to extract JSON
        import re
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            questions_data = json.loads(json_match.group())
            return [QuizQuestion(**q) for q in questions_data]
        else:
            # Fallback questions if AI parsing fails
            return [
                QuizQuestion(
                    question=f"What is the main concept of {topic}?",
                    options=["Option A", "Option B", "Option C", "Option D"],
                    correct_answer=0,
                    explanation=f"This relates to the fundamental principles of {topic}."
                )
            ]
    except Exception as e:
        logging.error(f"AI quiz generation error: {e}")
        return [
            QuizQuestion(
                question=f"What is {topic}?",
                options=["A concept", "A theory", "A practice", "All of the above"],
                correct_answer=3,
                explanation="This is a sample question as AI generation failed."
            )
        ]

async def answer_question(question: str, subject: str, grade_level: str = "general") -> str:
    """Generate AI answer for student question"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""You are a helpful tutor answering questions for {grade_level} students in {subject}.

Question: {question}

Please provide a clear, educational answer that is:
1. Appropriate for {grade_level} level understanding
2. Accurate and well-explained
3. Includes examples when helpful
4. Encourages further learning

Answer:"""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"AI answer generation error: {e}")
        return "I'm having trouble generating an answer right now. Please try again or consult your teacher."

async def generate_personalized_learning_path(student_id: str) -> LearningPath:
    """Generate personalized learning path using Gemini AI"""
    try:
        # Get student's quiz history and performance
        attempts = await db.quiz_attempts.find({"student_id": student_id}).to_list(100)
        questions = await db.questions.find({"student_id": student_id}).to_list(100)
        
        # Analyze performance by subject
        subject_performance = {}
        for attempt in attempts:
            quiz = await db.quizzes.find_one({"id": attempt["quiz_id"]})
            if quiz:
                subject = quiz["subject"]
                if subject not in subject_performance:
                    subject_performance[subject] = {"scores": [], "topics": []}
                subject_performance[subject]["scores"].append(attempt["percentage"])
        
        # Generate AI-powered recommendations
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        performance_summary = f"Student Performance Analysis:\n"
        for subject, data in subject_performance.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            performance_summary += f"- {subject}: Average {avg_score:.1f}%\n"
        
        if not performance_summary.strip().endswith("Analysis:"):
            performance_summary += f"- Total Questions Asked: {len(questions)}\n"
            performance_summary += f"- Total Quizzes Taken: {len(attempts)}\n"
        
        prompt = f"""Analyze this student's performance and create personalized learning recommendations:

{performance_summary}

Please provide a JSON response with:
1. "current_level": Assessment of student's level (beginner/intermediate/advanced)
2. "recommended_topics": Array of 5 topics to study next
3. "weak_areas": Array of 3 areas that need improvement  
4. "strong_areas": Array of 3 areas where student excels

Format as valid JSON:
{{
  "current_level": "intermediate",
  "recommended_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "weak_areas": ["area1", "area2", "area3"],
  "strong_areas": ["area1", "area2", "area3"]
}}"""

        response = model.generate_content(prompt)
        
        # Parse AI response (with fallback)
        try:
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                ai_recommendations = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found")
        except:
            # Fallback recommendations
            ai_recommendations = {
                "current_level": "intermediate",
                "recommended_topics": ["Mathematics Review", "Science Fundamentals", "Reading Comprehension", "Problem Solving", "Critical Thinking"],
                "weak_areas": ["Complex Problem Solving", "Advanced Mathematics", "Scientific Analysis"],
                "strong_areas": ["Basic Concepts", "Memory Recall", "Pattern Recognition"]
            }
        
        # Create learning path
        learning_path = LearningPath(
            student_id=student_id,
            subject="General",
            current_level=ai_recommendations.get("current_level", "intermediate"),
            recommended_topics=ai_recommendations.get("recommended_topics", []),
            weak_areas=ai_recommendations.get("weak_areas", []),
            strong_areas=ai_recommendations.get("strong_areas", []),
            next_recommendations=ai_recommendations.get("recommended_topics", [])[:3]
        )
        
        return learning_path
        
    except Exception as e:
        logging.error(f"Learning path generation error: {e}")
        # Return default learning path
        return LearningPath(
            student_id=student_id,
            subject="General",
            current_level="intermediate",
            recommended_topics=["Basic Mathematics", "Reading Skills", "Science Fundamentals"],
            weak_areas=["Problem Solving"],
            strong_areas=["Memory"],
            next_recommendations=["Practice Problems", "Reading Exercises", "Science Projects"]
        )

async def generate_progress_report(student_id: str, parent_id: str) -> dict:
    """Generate comprehensive progress report for parents using Gemini AI"""
    try:
        # Get student information
        student = await db.users.find_one({"id": student_id})
        if not student:
            raise ValueError("Student not found")
        
        # Get performance data
        quiz_attempts = await db.quiz_attempts.find({"student_id": student_id}).to_list(100)
        questions_asked = await db.questions.find({"student_id": student_id}).to_list(100)
        learning_path = await db.learning_paths.find_one({"student_id": student_id})
        
        # Calculate statistics
        total_quizzes = len(quiz_attempts)
        average_score = sum([attempt["percentage"] for attempt in quiz_attempts]) / total_quizzes if total_quizzes > 0 else 0
        
        # Subject-wise performance
        subject_stats = {}
        for attempt in quiz_attempts:
            quiz = await db.quizzes.find_one({"id": attempt["quiz_id"]})
            if quiz:
                subject = quiz["subject"]
                if subject not in subject_stats:
                    subject_stats[subject] = {"attempts": 0, "total_score": 0, "latest_score": 0}
                subject_stats[subject]["attempts"] += 1
                subject_stats[subject]["total_score"] += attempt["percentage"]
                subject_stats[subject]["latest_score"] = attempt["percentage"]
        
        # Calculate averages
        for subject in subject_stats:
            subject_stats[subject]["average_score"] = subject_stats[subject]["total_score"] / subject_stats[subject]["attempts"]
        
        # Recent activity
        recent_activities = []
        for attempt in sorted(quiz_attempts, key=lambda x: x["completed_at"], reverse=True)[:5]:
            quiz = await db.quizzes.find_one({"id": attempt["quiz_id"]})
            if quiz:
                recent_activities.append({
                    "type": "quiz_attempt",
                    "title": quiz["title"],
                    "score": attempt["percentage"],
                    "date": attempt["completed_at"]
                })
        
        # Generate AI insights
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        performance_data = f"Student: {student['name']}\nTotal Quizzes: {total_quizzes}\nAverage Score: {average_score:.1f}%\nQuestions Asked: {len(questions_asked)}"
        
        prompt = f"""As an educational progress analyst, analyze this student's performance data:

{performance_data}

Subject Performance:
{json.dumps(subject_stats, indent=2)}

Please provide:
1. A brief, positive progress summary (2-3 sentences)
2. 3 specific, actionable recommendations for parents to help their child improve
3. Highlight any strengths and areas for growth

Keep it encouraging and constructive for parents."""

        response = model.generate_content(prompt)
        ai_insights = response.text
        
        return {
            "student_info": {
                "name": student["name"],
                "email": student["email"],
                "id": student_id
            },
            "overall_performance": {
                "total_quizzes": total_quizzes,
                "average_score": round(average_score, 2),
                "total_questions_asked": len(questions_asked),
                "performance_trend": "improving" if average_score > 70 else "needs_attention"
            },
            "subject_performance": subject_stats,
            "recent_activities": recent_activities,
            "learning_path": {
                "current_level": learning_path["current_level"] if learning_path else "Not assessed",
                "strong_areas": learning_path["strong_areas"] if learning_path else [],
                "weak_areas": learning_path["weak_areas"] if learning_path else [],
                "recommended_topics": learning_path["recommended_topics"] if learning_path else []
            },
            "ai_insights": ai_insights,
            "report_generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Progress report generation error: {e}")
        return {
            "error": "Failed to generate progress report",
            "message": str(e)
        }

# ============= AUTH ROUTES =============


# === TOKEN UTILS ===
def generate_verification_token(email: str):
    """Generate a time-limited JWT token for email verification."""
    expire = datetime.utcnow() + timedelta(minutes=EMAIL_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire}
    token = jwt.encode(payload, EMAIL_SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_verification_token(token: str):
    """Decode and verify the verification JWT."""
    try:
        payload = jwt.decode(token, EMAIL_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None




# === EMAIL UTILS ===
async def send_verification_email(recipient_email: str, verification_link: str):
    """Send email verification link via Gmail SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify Your Email Address"
        msg["From"] = EMAIL_USER
        msg["To"] = recipient_email

        html_content = f"""
        <html>
        <body>
            <h2>Welcome to Our App!</h2>
            <p>Click the button below to verify your email address:</p>
            <a href="{verification_link}"
               style="background-color:#4CAF50;color:white;
                      padding:10px 15px;text-decoration:none;
                      border-radius:5px;">Verify Email</a>
            <p>This link will expire in 30 minutes.</p>
            <br>
            <p>If you didn't sign up, please ignore this email.</p>
            <p>Edumate Team</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, recipient_email, msg.as_string())

        print(f"✅ Verification email sent to {recipient_email}")

    except Exception as e:
        print(f"❌ Failed to send verification email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    allowed_signup_roles = {UserRoles.STUDENT, UserRoles.TEACHER, UserRoles.PARENT}
    if user_data.role not in allowed_signup_roles:
        raise HTTPException(status_code=403, detail="This role cannot be registered from signup")

    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user and existing_user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Email already registered and verified")

    trial_start_at = datetime.utcnow() if user_data.role == UserRoles.STUDENT else None
    trial_end_at = (
        trial_start_at + timedelta(days=SUBSCRIPTION_TRIAL_DAYS)
        if user_data.role == UserRoles.STUDENT
        else None
    )

    user = User(
        **user_data.dict(exclude={"password"}),
        id=str(uuid.uuid4()),
        trial_start_at=trial_start_at,
        trial_end_at=trial_end_at,
        is_blocked=False,
    )
    
    # Hash password and store
    user_dict = user.dict()
    user_dict["password"] = hash_password(user_data.password)

    # Insert or update
    if existing_user:
        await db.users.update_one({"email": user_data.email}, {"$set": user_dict})
    else:
        await db.users.insert_one(user_dict)

    # Generate JWT verification token
    token = generate_verification_token(user_data.email)
    verification_link = f"{FRONTEND_URL}verify-email/{token}"

    # Send verification email
    await send_verification_email(user_data.email, verification_link)

    return {"message": "Verification email sent."}

@api_router.get("/auth/verify-email/{token}")
async def verify_email(token: str):
    email = verify_verification_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user_doc = await db.users.find_one({"email": email})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    if user_doc.get("is_verified"):
        access_token = create_access_token({"sub": user_doc["id"]})
        user = User(**{k: v for k, v in user_doc.items() if k != "password"})
        return {
            "message": "User already verified",
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }

    await db.users.update_one(
        {"email": email},
        {"$set": {"is_verified": True, "verified_at": datetime.utcnow()}}
    )

    updated_doc = await db.users.find_one({"email": email})
    access_token = create_access_token({"sub": updated_doc["id"]})
    user = User(**{k: v for k, v in updated_doc.items() if k != "password"})
    return {
        "message": "Email verified successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }

@api_router.post("/auth/resend-verification")
async def resend_verification(email: EmailStr):
    user_doc = await db.users.find_one({"email": email})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    if user_doc.get("is_verified"):
        return {"message": "User already verified"}

    # Generate new token
    token = generate_verification_token(email)
    verification_link = f"{FRONTEND_URL}verify-email/{token}"

    await send_verification_email(email, verification_link)

    return {"message": "New verification email sent"}


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    user_doc = await db.users.find_one({"email": login_data.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user_doc.get("is_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email before logging in")

    if not verify_password(login_data.password, user_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user_doc.get("is_blocked"):
        raise HTTPException(status_code=403, detail=user_doc.get("blocked_reason") or "Your account is blocked")

    if user_doc.get("role") == UserRoles.STUDENT:
        student_access = await build_student_access_context(user_doc)
        if student_access.get("status") == "PAYMENT_REQUIRED":
            user_doc["student_access"] = student_access

    access_token = create_access_token({"sub": user_doc["id"]})
    user = User(**{k: v for k, v in user_doc.items() if k != "password"})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )


@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# ============= STUDY CONTENT ROUTES =============

@api_router.post("/study/generate", response_model=StudyContent)
async def generate_study_content_route(
    content_data: StudyContentCreate,
    current_user: User = Depends(get_current_user)
):
    # Generate AI content
    ai_content = await generate_study_content(
        content_data.topic, 
        content_data.subject, 
        content_data.grade_level
    )
    
    # Create study content record
    study_content = StudyContent(
        title=content_data.title,
        subject=content_data.subject,
        grade_level=content_data.grade_level,
        content=ai_content,
        created_by=current_user.id,
        tags=content_data.tags
    )
    
    # Save to database
    await db.study_content.insert_one(study_content.dict())
    
    return study_content

@api_router.get("/study/content", response_model=List[StudyContent])
async def get_study_content(
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if subject:
        query["subject"] = subject
    if grade_level:
        query["grade_level"] = grade_level
        
    content_list = await db.study_content.find(query).to_list(100)
    return [StudyContent(**content) for content in content_list]


@api_router.get("/teacher/my-contents", response_model=List[StudyContent])
async def get_teacher_contents(current_user: User = Depends(get_current_user)):
    """Return only the study contents created by the current teacher"""
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")

    try:
        contents = await db.study_content.find({"created_by": current_user.id}).to_list(100)
        return [StudyContent(**content) for content in contents]
    except Exception as e:
        logging.error(f"Error fetching teacher contents: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch teacher contents")


@api_router.put("/teacher/update-content/{content_id}", response_model=StudyContent)
async def update_study_content(
    content_id: str,
    update_data: StudyContentCreate,
    current_user: User = Depends(get_current_user)
):
    """Allow only the teacher who created the content to update it"""
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")

    try:
        existing = await db.study_content.find_one({"_id": ObjectId(content_id)})

        if not existing:
            raise HTTPException(status_code=404, detail="Content not found")

        if existing["created_by"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can update only your own contents")

        updated_content = {
            "title": update_data.title,
            "subject": update_data.subject,
            "grade_level": update_data.grade_level,
            "tags": update_data.tags,
            "content": update_data.content  # optional: keep old AI content if not updated
        }

        await db.study_content.update_one(
            {"_id": ObjectId(content_id)},
            {"$set": updated_content}
        )

        updated = await db.study_content.find_one({"_id": ObjectId(content_id)})
        return StudyContent(**updated)

    except Exception as e:
        logging.error(f"Error updating content: {e}")
        raise HTTPException(status_code=500, detail="Failed to update study content")


@api_router.delete("/teacher/delete-content/{content_id}")
async def delete_study_content(
    content_id: str,
    current_user: User = Depends(get_current_user)
):
    """Allow teacher to delete their own study content"""
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")

    try:
        existing = await db.study_content.find_one({"_id": ObjectId(content_id)})

        if not existing:
            raise HTTPException(status_code=404, detail="Content not found")

        if existing["created_by"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can delete only your own contents")

        await db.study_content.delete_one({"_id": ObjectId(content_id)})
        return {"message": "Study content deleted successfully"}

    except Exception as e:
        logging.error(f"Error deleting content: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete study content")


# ============= QUIZ ROUTES =============

@api_router.post("/quiz/generate", response_model=Quiz)
async def generate_quiz_route(
    quiz_data: QuizCreate,
    current_user: User = Depends(get_current_user)
):
    # Generate AI questions
    questions = await generate_quiz(
        quiz_data.topic,
        quiz_data.subject,
        quiz_data.grade_level,
        quiz_data.num_questions,
        quiz_data.difficulty
    )
    
    # Create quiz
    quiz = Quiz(
        title=quiz_data.title,
        subject=quiz_data.subject,
        grade_level=quiz_data.grade_level,
        questions=questions,
        created_by=current_user.id,
        total_marks=len(questions)
    )
    
    # Save to database
    await db.quizzes.insert_one(quiz.dict())
    
    return quiz

@api_router.get("/quiz/list")
async def get_quizzes(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if subject:
        query["subject"] = subject
    
    # Teachers see only their quizzes, students see all quizzes
    if current_user.role == "teacher":
        query["created_by"] = current_user.id
        
    quizzes = await db.quizzes.find(query).to_list(100)
    
    # Clean ObjectId from response
    clean_quizzes = []
    for quiz in quizzes:
        if "_id" in quiz:
            del quiz["_id"]
        clean_quizzes.append(quiz)
    
    return clean_quizzes

@api_router.post("/quiz/{quiz_id}/attempt", response_model=QuizAttempt)
async def submit_quiz_attempt(
    quiz_id: str,
    answers: Dict[str, int],
    current_user: User = Depends(get_current_user)
):
    # Get quiz
    quiz_doc = await db.quizzes.find_one({"id": quiz_id})
    if not quiz_doc:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    quiz = Quiz(**quiz_doc)
    
    # Calculate score
    correct_answers = 0
    for q_idx, selected_option in answers.items():
        if int(q_idx) < len(quiz.questions):
            if quiz.questions[int(q_idx)].correct_answer == selected_option:
                correct_answers += 1
    
    score = correct_answers
    percentage = (score / len(quiz.questions)) * 100 if quiz.questions else 0
    
    # Create attempt record
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        student_id=current_user.id,
        answers=answers,
        score=score,
        total_marks=len(quiz.questions),
        percentage=percentage,
        time_taken=30  # TODO: Track actual time
    )
    
    # Save attempt (answers already have string keys)
    await db.quiz_attempts.insert_one(attempt.dict())
    
    # Trigger AI analysis asynchronously
    try:
        await analyze_quiz_result(current_user.id, quiz_id, attempt.id)
    except Exception as e:
        logging.error(f"Quiz analysis failed: {e}")
        # Don't fail the quiz submission if analysis fails
    
    return attempt

# ============= Q&A ROUTES =============

@api_router.post("/qa/ask", response_model=Question)
async def ask_question(
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_user)
):
    # Generate AI answer
    ai_answer = await answer_question(
        question_data.question,
        question_data.subject
    )
    
    # Create question record
    question = Question(
        student_id=current_user.id,
        question=question_data.question,
        subject=question_data.subject,
        answer=ai_answer,
        answered_at=datetime.utcnow()
    )
    
    # Save to database
    await db.questions.insert_one(question.dict())
    
    return question

@api_router.get("/qa/questions", response_model=List[Question])
async def get_questions(
    current_user: User = Depends(get_current_user)
):
    query = {}
    if current_user.role == "student":
        query["student_id"] = current_user.id
        
    questions = await db.questions.find(query).to_list(100)
    return [Question(**q) for q in questions]

# ============= PROGRESS ROUTES =============

@api_router.get("/progress/student/{student_id}", response_model=Dict)
async def get_student_progress(
    student_id: str,
    current_user: User = Depends(get_current_user)
):
    # Check permissions
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get quiz attempts
    attempts = await db.quiz_attempts.find({"student_id": student_id}).to_list(100)
    
    # Get questions asked
    questions = await db.questions.find({"student_id": student_id}).to_list(100)
    
    # Calculate stats
    total_quizzes = len(attempts)
    average_score = sum([a["percentage"] for a in attempts]) / total_quizzes if total_quizzes > 0 else 0
    total_questions = len(questions)
    
    # Get subjects breakdown
    subject_stats = {}
    for attempt in attempts:
        quiz = await db.quizzes.find_one({"id": attempt["quiz_id"]})
        if quiz:
            subject = quiz["subject"]
            if subject not in subject_stats:
                subject_stats[subject] = {"total_attempts": 0, "avg_score": 0, "scores": []}
            subject_stats[subject]["total_attempts"] += 1
            subject_stats[subject]["scores"].append(attempt["percentage"])
    
    # Calculate averages
    for subject in subject_stats:
        scores = subject_stats[subject]["scores"]
        subject_stats[subject]["avg_score"] = sum(scores) / len(scores) if scores else 0
        del subject_stats[subject]["scores"]  # Remove raw scores
    
    return {
        "student_id": student_id,
        "total_quizzes": total_quizzes,
        "average_score": round(average_score, 2),
        "total_questions_asked": total_questions,
        "subject_breakdown": subject_stats,
        "recent_activities": {
            "last_quiz": attempts[-1]["completed_at"] if attempts else None,
            "last_question": questions[-1]["created_at"] if questions else None
        }
    }

# ============= CHAT ROUTES =============

@api_router.post("/chat/send", response_model=ChatMessage)
async def send_message(
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user)
):
    message = ChatMessage(
        sender_id=current_user.id,
        receiver_id=message_data.receiver_id,
        message=message_data.message
    )
    
    await db.chat_messages.insert_one(message.dict())
    
    return message

@api_router.get("/chat/conversations", response_model=List[ChatMessage])
async def get_conversations(
    with_user: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {
        "$or": [
            {"sender_id": current_user.id},
            {"receiver_id": current_user.id}
        ]
    }
    
    if with_user:
        query = {
            "$or": [
                {"sender_id": current_user.id, "receiver_id": with_user},
                {"sender_id": with_user, "receiver_id": current_user.id}
            ]
        }
    
    messages = await db.chat_messages.find(query).sort("timestamp", 1).to_list(100)
    return [ChatMessage(**msg) for msg in messages]

# ============= DASHBOARD ROUTES =============
from bson import ObjectId

def fix_objectids(obj):
    """Recursively convert ObjectId to str in MongoDB documents."""
    if isinstance(obj, list):
        return [fix_objectids(item) for item in obj]
    elif isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if isinstance(v, ObjectId):
                new_obj[k] = str(v)
            else:
                new_obj[k] = fix_objectids(v)
        return new_obj
    else:
        return obj

@api_router.get("/dashboard/student")
async def get_student_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required")

    access_status = current_user.student_access or await build_student_access_context(current_user.dict())

    if not access_status.get("access_allowed"):
        return {
            "user": fix_objectids(current_user.dict() if hasattr(current_user, "dict") else current_user),
            "recent_quiz_attempts": [],
            "recent_questions": [],
            "available_content": [],
            "available_quizzes": [],
            "quick_stats": {"total_quizzes_taken": 0, "questions_asked": 0},
            "access_status": access_status,
        }

    # Fetch and convert data
    recent_quizzes = fix_objectids(
        await db.quiz_attempts.find({"student_id": current_user.id})
        .sort("completed_at", -1)
        .to_list(5)
    )

    recent_questions = fix_objectids(
        await db.questions.find({"student_id": current_user.id})
        .sort("created_at", -1)
        .to_list(5)
    )

    available_content = fix_objectids(
        await db.study_content.find({}).sort("created_at", -1).to_list(10)
    )

    available_quizzes = fix_objectids(
        await db.quizzes.find({}).sort("created_at", -1).to_list(10)
    )

    quick_stats = {
        "total_quizzes_taken": len(
            await db.quiz_attempts.find({"student_id": current_user.id}).to_list(1000)
        ),
        "questions_asked": len(
            await db.questions.find({"student_id": current_user.id}).to_list(1000)
        )
    }

    return {
        "user": fix_objectids(current_user.dict() if hasattr(current_user, "dict") else current_user),
        "recent_quiz_attempts": recent_quizzes,
        "recent_questions": recent_questions,
        "available_content": available_content,
        "available_quizzes": available_quizzes,
        "quick_stats": quick_stats,
        "access_status": access_status,
    }

@api_router.get("/dashboard/teacher")
async def get_teacher_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")

    # Get created content
    my_content = await db.study_content.find({"created_by": current_user.id}).sort("created_at", -1).to_list(100)
    my_quizzes = await db.quizzes.find({"created_by": current_user.id}).sort("created_at", -1).to_list(100)

    # Get student activities on my content
    my_quiz_ids = [quiz["_id"] for quiz in my_quizzes]  # ✅ use "_id", not "id"
    quiz_attempts = await db.quiz_attempts.find({"quiz_id": {"$in": my_quiz_ids}}).sort("completed_at", -1).to_list(100)

    result = {
        "user": fix_objectids(current_user.dict() if hasattr(current_user, "dict") else current_user),
        "my_content": fix_objectids(my_content),
        "my_quizzes": fix_objectids(my_quizzes),
        "recent_quiz_attempts": fix_objectids(quiz_attempts),
        "stats": {
            "total_content_created": len(my_content),
            "total_quizzes_created": len(my_quizzes),
            "total_student_attempts": len(quiz_attempts)
        }
    }

    return fix_objectids(result)



# ============= PAYMENT ROUTES =============

@api_router.get("/subscription-plans")
async def get_subscription_plans():
    return {"plans": list_subscription_plans()}


@api_router.post("/create-subscription")
async def create_subscription(
    subscription_request: SubscriptionRequest,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRoles.STUDENT:
        raise HTTPException(status_code=403, detail="Student access required")

    plan = get_subscription_plan(subscription_request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    if current_user.is_blocked:
        raise HTTPException(status_code=403, detail=current_user.blocked_reason or "Your account is blocked")

    active_subscription = await get_active_student_subscription(current_user.id)
    if active_subscription:
        raise HTTPException(
            status_code=409,
            detail=f"An active {active_subscription.get('plan_name', 'subscription')} already exists",
        )

    pending_subscriptions = await db.subscriptions.find(
        {"student_id": current_user.id, "status": "PENDING"}
    ).sort("created_at", -1).to_list(10)
    if pending_subscriptions:
        pending_ids = [sub.get("id") for sub in pending_subscriptions if sub.get("id")]
        pending_payment = await db.payments.find_one(
            {
                "$or": [
                    {"subscription_id": {"$in": pending_ids}},
                    {"transaction_id": {"$in": pending_ids}},
                ],
                "status": {"$in": ["INITIATED", "PENDING"]},
            }
        )
        if pending_payment:
            raise HTTPException(
                status_code=409,
                detail="A subscription payment is already pending. Please complete or wait for confirmation.",
            )

    transaction_id = f"SUB_{current_user.id}_{uuid.uuid4().hex[:10]}"
    dates = calculate_subscription_dates(subscription_request.plan_id)
    now = datetime.utcnow()

    latest_subscription = await get_latest_student_subscription(current_user.id)
    await store_previous_subscription_snapshot(
        current_user.id,
        latest_subscription,
        source="create_subscription",
        action_by=current_user.id,
        reason="Before creating a new subscription",
    )

    await db.subscriptions.update_many(
        {"student_id": current_user.id, "status": "PENDING"},
        {"$set": {"status": "INACTIVE", "updated_at": now}},
    )

    checkout = await create_phonepe_checkout_order(transaction_id, current_user.id, plan)

    subscription = Subscription(
        id=transaction_id,
        student_id=current_user.id,
        plan_id=plan["id"],
        plan_name=plan["name"],
        billing_cycle=plan["billing_cycle"],
        status="PENDING",
        start_date=dates["start_date"],
        end_date=dates["end_date"],
        amount=plan["amount"],
        next_billing_date=dates["next_billing_date"],
        auto_renewal=True,
        created_at=now,
        updated_at=now,
    )
    await db.subscriptions.insert_one(subscription.dict())

    payment_record = PaymentRecord(
        transaction_id=transaction_id,
        subscription_id=transaction_id,
        student_id=current_user.id,
        plan_id=plan["id"],
        plan_name=plan["name"],
        billing_cycle=plan["billing_cycle"],
        amount=plan["amount"],
        payment_type="subscription",
        status="INITIATED",
        description=f"Subscription to {plan['name']}",
        provider="phonepe",
        merchant_order_id=transaction_id,
        provider_order_id=checkout["provider_order_id"],
        provider_response=checkout["provider_response"],
    )
    await db.payments.insert_one(payment_record.dict())

    return {
        "success": True,
        "transaction_id": transaction_id,
        "merchant_order_id": transaction_id,
        "amount": plan["amount"],
        "billing_cycle": plan["billing_cycle"],
        "redirect_url": checkout["redirect_url"],
        "message": "Subscription order created successfully",
    }


@api_router.get("/payment-status/{transaction_id}")
async def get_payment_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user)
):
    payment = await db.payments.find_one({"transaction_id": transaction_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if current_user.role == UserRoles.STUDENT and payment.get("student_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await finalize_payment_status(transaction_id, current_user=current_user)
    return {
        "transaction_id": transaction_id,
        "status": result["payment_status"],
        "gateway_status": result["gateway_status"],
        "subscription": result["subscription"],
    }


@api_router.post("/payments/phonepe/confirm/{transaction_id}")
async def confirm_phonepe_payment(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
):
    result = await finalize_payment_status(transaction_id, current_user=current_user)
    return {
        "success": result["payment_status"] == "SUCCESS",
        "transaction_id": transaction_id,
        "payment_status": result["payment_status"],
        "gateway_status": result["gateway_status"],
        "subscription": result["subscription"],
    }


@api_router.post("/payments/phonepe/webhook")
async def handle_phonepe_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    merchant_order_id = (
        payload.get("merchantOrderId")
        or payload.get("data", {}).get("merchantOrderId")
        or payload.get("payload", {}).get("merchantOrderId")
    )

    if not merchant_order_id:
        return {"received": True, "processed": False, "message": "merchantOrderId not present"}

    try:
        await finalize_payment_status(merchant_order_id)
        return {"received": True, "processed": True}
    except Exception as exc:
        logging.error(f"PhonePe webhook processing error: {exc}")
        return {"received": True, "processed": False, "message": str(exc)}


# ============= ADMIN USER MANAGEMENT ROUTES =============

async def get_admin_stats_snapshot(now: datetime) -> Dict[str, Any]:
    start_of_day = datetime(now.year, now.month, now.day)
    start_of_month = datetime(now.year, now.month, 1)
    start_30_days = start_of_day - timedelta(days=29)

    (
        total_users,
        students,
        teachers,
        parents,
        admins,
        blocked,
        blocked_students,
        registrations_today,
        registrations_this_month,
        paid_history_student_ids,
    ) = await asyncio.gather(
        db.users.count_documents({}),
        db.users.count_documents({"role": UserRoles.STUDENT}),
        db.users.count_documents({"role": UserRoles.TEACHER}),
        db.users.count_documents({"role": UserRoles.PARENT}),
        db.users.count_documents({"role": UserRoles.ADMIN}),
        db.users.count_documents({"is_blocked": True}),
        db.users.count_documents({"role": UserRoles.STUDENT, "is_blocked": True}),
        db.users.count_documents({"created_at": {"$gte": start_of_day}}),
        db.users.count_documents({"created_at": {"$gte": start_of_month}}),
        db.payments.distinct("student_id", {"payment_type": "subscription", "status": "SUCCESS"}),
    )

    active_subscription_rows = await db.subscriptions.aggregate(
        [
            {"$match": {"status": "ACTIVE", "end_date": {"$gt": now}}},
            {"$sort": {"updated_at": -1}},
            {"$group": {"_id": "$student_id", "subscription": {"$first": "$$ROOT"}}},
            {"$project": {"_id": 0, "subscription": 1}},
        ]
    ).to_list(50000)
    active_subscriptions = [row.get("subscription") for row in active_subscription_rows if row.get("subscription")]
    active_subscription_count = len(active_subscriptions)
    active_student_ids = [sub.get("student_id") for sub in active_subscriptions if sub.get("student_id")]

    monthly_subscribers = sum(1 for sub in active_subscriptions if (sub.get("billing_cycle") or "").lower() == "monthly")
    yearly_subscribers = sum(1 for sub in active_subscriptions if (sub.get("billing_cycle") or "").lower() == "yearly")

    trial_active_filter: Dict[str, Any] = {"role": UserRoles.STUDENT, "trial_end_at": {"$gt": now}}
    trial_ended_filter: Dict[str, Any] = {"role": UserRoles.STUDENT, "trial_end_at": {"$lte": now}}
    free_tier_filter: Dict[str, Any] = {"role": UserRoles.STUDENT, "trial_end_at": {"$gt": now}}
    if active_student_ids:
        trial_active_filter["id"] = {"$nin": active_student_ids}
        trial_ended_filter["id"] = {"$nin": active_student_ids}
        free_tier_filter["id"] = {"$nin": active_student_ids}
    if paid_history_student_ids:
        free_tier_filter["id"] = {
            "$nin": list(set((free_tier_filter.get("id") or {}).get("$nin", []) + paid_history_student_ids))
        }

    free_trial_active_users, free_trial_ended_users, free_tier_users = await asyncio.gather(
        db.users.count_documents(trial_active_filter),
        db.users.count_documents(trial_ended_filter),
        db.users.count_documents(free_tier_filter),
    )

    payments_today_agg, payments_month_agg = await asyncio.gather(
        db.payments.aggregate(
            [
                {"$match": {"status": "SUCCESS", "paid_at": {"$gte": start_of_day}}},
                {"$group": {"_id": None, "amount": {"$sum": "$amount"}, "count": {"$sum": 1}}},
            ]
        ).to_list(1),
        db.payments.aggregate(
            [
                {"$match": {"status": "SUCCESS", "paid_at": {"$gte": start_of_month}}},
                {"$group": {"_id": None, "amount": {"$sum": "$amount"}, "count": {"$sum": 1}}},
            ]
        ).to_list(1),
    )

    payments_today = payments_today_agg[0] if payments_today_agg else {"amount": 0, "count": 0}
    payments_month = payments_month_agg[0] if payments_month_agg else {"amount": 0, "count": 0}

    user_growth_raw = await db.users.aggregate(
        [
            {"$match": {"created_at": {"$gte": start_30_days}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
    ).to_list(200)
    growth_map = {row["_id"]: row["count"] for row in user_growth_raw}
    user_growth_labels: List[str] = []
    user_growth_values: List[int] = []
    for offset in range(30):
        day = start_30_days + timedelta(days=offset)
        key = day.strftime("%Y-%m-%d")
        user_growth_labels.append(day.strftime("%d %b"))
        user_growth_values.append(int(growth_map.get(key, 0)))

    payment_growth_raw = await db.payments.aggregate(
        [
            {"$match": {"status": "SUCCESS", "paid_at": {"$gte": start_30_days}}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$paid_at"}},
                    "amount": {"$sum": "$amount"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
    ).to_list(200)
    payment_growth_map = {row["_id"]: row["amount"] for row in payment_growth_raw}
    payment_growth_values: List[int] = []
    for offset in range(30):
        day = start_30_days + timedelta(days=offset)
        key = day.strftime("%Y-%m-%d")
        payment_growth_values.append(int(payment_growth_map.get(key, 0)))

    return {
        "total_users": total_users,
        "students": students,
        "teachers": teachers,
        "parents": parents,
        "admins": admins,
        "blocked": blocked,
        "blocked_students": blocked_students,
        "active_subscriptions": active_subscription_count,
        "monthly_subscribers": monthly_subscribers,
        "yearly_subscribers": yearly_subscribers,
        "free_tier_users": free_tier_users,
        "free_trial_active_users": free_trial_active_users,
        "free_trial_ended_users": free_trial_ended_users,
        "registrations_today": registrations_today,
        "registrations_this_month": registrations_this_month,
        "payments_collected_today": int(payments_today.get("amount", 0)),
        "payments_count_today": int(payments_today.get("count", 0)),
        "payments_collected_this_month": int(payments_month.get("amount", 0)),
        "payments_count_this_month": int(payments_month.get("count", 0)),
        "user_growth": {"labels": user_growth_labels, "values": user_growth_values},
        "payment_growth": {"labels": user_growth_labels, "values": payment_growth_values},
        "subscription_distribution": [
            {"label": "Free Tier", "value": free_tier_users},
            {"label": "Trial Ended", "value": free_trial_ended_users},
            {"label": "Monthly", "value": monthly_subscribers},
            {"label": "Yearly", "value": yearly_subscribers},
            {"label": "Blocked Students", "value": blocked_students},
        ],
    }


@api_router.get("/admin/overview")
async def get_admin_overview(current_user: User = Depends(get_current_user)):
    ensure_admin_role(current_user)
    now = datetime.utcnow()
    stats = await get_admin_stats_snapshot(now)
    return {
        "stats": stats,
        "as_of": now,
        "analytics": {
            "user_growth": stats.get("user_growth"),
            "payment_growth": stats.get("payment_growth"),
            "subscription_distribution": stats.get("subscription_distribution"),
        },
    }


@api_router.get("/admin/users")
async def get_admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    ensure_admin_role(current_user)
    now = datetime.utcnow()

    base_match: Dict[str, Any] = {}
    if role and role.lower() != "all":
        base_match["role"] = role.lower()
    if search:
        escaped = re.escape(search.strip())
        base_match["email"] = {"$regex": escaped, "$options": "i"}

    status_map = {
        "blocked": {"admin_status": "BLOCKED"},
        "active_subscription": {"admin_status": "ACTIVE_SUBSCRIPTION"},
        "subscribed": {"admin_status": "ACTIVE_SUBSCRIPTION"},
        "trial_active": {"admin_status": "TRIAL_ACTIVE"},
        "payment_required": {"admin_status": "PAYMENT_REQUIRED"},
        "non_student": {"admin_status": "NON_STUDENT"},
        "free_tier": {"lifecycle_status": "FREE_TIER"},
        "free_trial_active": {"lifecycle_status": "FREE_TRIAL_ACTIVE"},
        "free_trial_ended": {"lifecycle_status": "FREE_TRIAL_ENDED"},
        "monthly_subscription": {"lifecycle_status": "MONTHLY_SUBSCRIPTION"},
        "yearly_subscription": {"lifecycle_status": "YEARLY_SUBSCRIPTION"},
    }

    aggregation_pipeline: List[Dict[str, Any]] = [
        {"$match": base_match},
        {"$project": {"_id": 0, "password": 0}},
        {
            "$lookup": {
                "from": "subscriptions",
                "let": {"user_id": "$id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$student_id", "$$user_id"]},
                                    {"$eq": ["$status", "ACTIVE"]},
                                    {"$gt": ["$end_date", now]},
                                ]
                            }
                        }
                    },
                    {"$sort": {"updated_at": -1}},
                    {"$limit": 1},
                    {"$project": {"_id": 0}},
                ],
                "as": "active_subscription_list",
            }
        },
        {"$addFields": {"active_subscription": {"$arrayElemAt": ["$active_subscription_list", 0]}}},
        {
            "$lookup": {
                "from": "subscriptions",
                "let": {"user_id": "$id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$student_id", "$$user_id"]}}},
                    {"$sort": {"created_at": -1}},
                    {"$limit": 1},
                    {"$project": {"_id": 0}},
                ],
                "as": "latest_subscription_list",
            }
        },
        {"$addFields": {"latest_subscription": {"$arrayElemAt": ["$latest_subscription_list", 0]}}},
        {
            "$addFields": {
                "admin_status": {
                    "$cond": [
                        {"$eq": ["$is_blocked", True]},
                        "BLOCKED",
                        {
                            "$cond": [
                                {"$ne": ["$role", UserRoles.STUDENT]},
                                "NON_STUDENT",
                                {
                                    "$cond": [
                                        {"$ne": ["$active_subscription", None]},
                                        "ACTIVE_SUBSCRIPTION",
                                        {
                                            "$cond": [
                                                {"$gt": ["$trial_end_at", now]},
                                                "TRIAL_ACTIVE",
                                                "PAYMENT_REQUIRED",
                                            ]
                                        },
                                    ]
                                },
                            ]
                        },
                    ]
                }
            }
        },
        {
            "$addFields": {
                "lifecycle_status": {
                    "$cond": [
                        {"$eq": ["$is_blocked", True]},
                        "BLOCKED",
                        {
                            "$cond": [
                                {"$ne": ["$role", UserRoles.STUDENT]},
                                "NON_STUDENT",
                                {
                                    "$cond": [
                                        {"$ne": ["$active_subscription", None]},
                                        {
                                            "$cond": [
                                                {"$eq": ["$active_subscription.billing_cycle", "yearly"]},
                                                "YEARLY_SUBSCRIPTION",
                                                "MONTHLY_SUBSCRIPTION",
                                            ]
                                        },
                                        {
                                            "$cond": [
                                                {"$gt": ["$trial_end_at", now]},
                                                {
                                                    "$cond": [
                                                        {
                                                            "$in": [
                                                                {"$ifNull": ["$latest_subscription.billing_cycle", ""]},
                                                                ["monthly", "yearly"],
                                                            ]
                                                        },
                                                        "FREE_TRIAL_ACTIVE",
                                                        "FREE_TIER",
                                                    ]
                                                },
                                                "FREE_TRIAL_ENDED",
                                            ]
                                        },
                                    ]
                                },
                            ]
                        },
                    ]
                }
            }
        },
    ]

    if status and status.lower() != "all":
        normalized_status = status.lower()
        if normalized_status == "unblocked":
            aggregation_pipeline.append({"$match": {"admin_status": {"$ne": "BLOCKED"}}})
        elif normalized_status in status_map:
            aggregation_pipeline.append({"$match": status_map[normalized_status]})

    skip = (page - 1) * page_size
    aggregation_pipeline.extend(
        [
            {"$sort": {"created_at": -1}},
            {
                "$facet": {
                    "users": [{"$skip": skip}, {"$limit": page_size}],
                    "meta": [{"$count": "total"}],
                }
            },
        ]
    )

    aggregate_result = await db.users.aggregate(aggregation_pipeline).to_list(1)
    payload = aggregate_result[0] if aggregate_result else {"users": [], "meta": []}
    user_rows = payload.get("users", [])
    total_records = payload.get("meta", [{}])[0].get("total", 0) if payload.get("meta") else 0

    for user in user_rows:
        active_subscription = user.get("active_subscription")
        latest_subscription = user.get("latest_subscription")
        selected_subscription = active_subscription or latest_subscription
        trial_end_at = user.get("trial_end_at")
        trial_days_remaining = 0
        if trial_end_at and trial_end_at > now:
            trial_days_remaining = max(0, (trial_end_at.date() - now.date()).days)

        access_message_map = {
            "BLOCKED": user.get("blocked_reason") or "Account blocked by admin",
            "ACTIVE_SUBSCRIPTION": "Paid subscription active",
            "TRIAL_ACTIVE": f"Free trial active for {trial_days_remaining} day(s)",
            "PAYMENT_REQUIRED": "Trial ended and no active subscription",
            "NON_STUDENT": "Not a student account",
            "FREE_TIER": f"Free tier active for {trial_days_remaining} day(s)",
            "FREE_TRIAL_ACTIVE": f"Free trial active for {trial_days_remaining} day(s)",
            "FREE_TRIAL_ENDED": "Free trial ended and no active subscription",
            "MONTHLY_SUBSCRIPTION": "Monthly subscription active",
            "YEARLY_SUBSCRIPTION": "Yearly subscription active",
        }
        lifecycle_status = user.get("lifecycle_status")
        admin_status = user.get("admin_status")

        user["student_access"] = {
            "status": admin_status,
            "lifecycle_status": lifecycle_status,
            "message": access_message_map.get(lifecycle_status) or access_message_map.get(admin_status) or "Unknown",
            "trial_end_at": trial_end_at,
            "trial_days_remaining": trial_days_remaining,
            "subscription": selected_subscription,
            "previous_subscription": user.get("previous_subscription"),
            "next_billing_date": (selected_subscription or {}).get("next_billing_date") or (selected_subscription or {}).get("end_date"),
            "access_allowed": lifecycle_status in {"FREE_TIER", "FREE_TRIAL_ACTIVE", "MONTHLY_SUBSCRIPTION", "YEARLY_SUBSCRIPTION"},
            "is_blocked": bool(user.get("is_blocked")),
        }

        user.pop("active_subscription_list", None)
        user.pop("active_subscription", None)
        user.pop("latest_subscription_list", None)
        user.pop("latest_subscription", None)

    stats = await get_admin_stats_snapshot(now)
    total_pages = (total_records + page_size - 1) // page_size if total_records else 0

    return {
        "users": user_rows,
        "stats": stats,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
            "has_next": page < total_pages,
        },
        "filters": {"role": role or "all", "status": status or "all", "search": search or ""},
    }


@api_router.post("/admin/users/{user_id}/block")
async def block_user(
    user_id: str,
    action: AdminUserAction,
    current_user: User = Depends(get_current_user),
):
    ensure_admin_role(current_user)
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.get("role") == UserRoles.ADMIN:
        raise HTTPException(status_code=400, detail="Admin accounts cannot be blocked")

    now = datetime.utcnow()
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "is_blocked": True,
                "blocked_reason": action.reason or "Blocked by admin",
                "blocked_at": now,
                "blocked_by": current_user.id,
            }
        },
    )
    return {"success": True, "message": "User blocked successfully"}


@api_router.post("/admin/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    ensure_admin_role(current_user)
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {"is_blocked": False},
            "$unset": {"blocked_reason": "", "blocked_at": "", "blocked_by": ""},
        },
    )
    return {"success": True, "message": "User unblocked successfully"}


@api_router.post("/admin/users/{user_id}/cancel-subscription")
async def cancel_user_subscription(
    user_id: str,
    action: AdminUserAction,
    current_user: User = Depends(get_current_user),
):
    ensure_admin_role(current_user)

    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.get("role") != UserRoles.STUDENT:
        raise HTTPException(status_code=400, detail="Only student subscriptions can be canceled")

    now = datetime.utcnow()
    existing_subscriptions = await db.subscriptions.find(
        {"student_id": user_id, "status": {"$in": ["ACTIVE", "PENDING"]}}
    ).sort("updated_at", -1).to_list(10)
    snapshot_source = None
    if existing_subscriptions:
        snapshot_source = next((s for s in existing_subscriptions if s.get("status") == "ACTIVE"), existing_subscriptions[0])
        await store_previous_subscription_snapshot(
            user_id,
            snapshot_source,
            source="admin_cancel",
            action_by=current_user.id,
            reason=action.reason or "Canceled by admin",
        )

    update_result = await db.subscriptions.update_many(
        {"student_id": user_id, "status": {"$in": ["ACTIVE", "PENDING"]}},
        {
            "$set": {
                "status": "CANCELED",
                "auto_renewal": False,
                "canceled_at": now,
                "canceled_by": current_user.id,
                "updated_at": now,
                "cancellation_reason": action.reason or "Canceled by admin",
            }
        },
    )

    return {
        "success": True,
        "updated_subscriptions": update_result.modified_count,
        "message": "Subscription canceled successfully",
    }


@api_router.post("/admin/users/{user_id}/restore-subscription")
async def restore_user_subscription(
    user_id: str,
    action: AdminRestoreSubscriptionRequest,
    current_user: User = Depends(get_current_user),
):
    ensure_admin_role(current_user)

    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.get("role") != UserRoles.STUDENT:
        raise HTTPException(status_code=400, detail="Only student subscriptions can be restored")

    now = datetime.utcnow()
    active_subscription = await get_active_student_subscription(user_id)
    if active_subscription:
        raise HTTPException(status_code=409, detail="User already has an active subscription")

    last_subscription = await get_latest_student_subscription(user_id)
    previous_snapshot = target_user.get("previous_subscription")
    restore_option = (action.restore_option or "previous").strip().lower()
    restore_plan_id = None

    if restore_option == "monthly":
        restore_plan_id = "monthly_199"
    elif restore_option == "yearly":
        restore_plan_id = "yearly_1799"
    elif restore_option == "previous":
        restore_plan_id = (previous_snapshot or {}).get("plan_id") or (last_subscription or {}).get("plan_id")
        if not restore_plan_id:
            raise HTTPException(status_code=400, detail="No previous subscription available to restore")
    else:
        raise HTTPException(status_code=400, detail="restore_option must be one of: previous, monthly, yearly")

    plan = get_subscription_plan(restore_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Selected restore plan is not available")

    dates = calculate_subscription_dates(plan["id"], now)

    restore_subscription_id = f"ADMIN_RESTORE_{user_id}_{uuid.uuid4().hex[:8]}"
    restored_subscription = Subscription(
        id=restore_subscription_id,
        student_id=user_id,
        plan_id=plan["id"],
        plan_name=plan["name"],
        billing_cycle=plan["billing_cycle"],
        status="ACTIVE",
        start_date=dates["start_date"],
        end_date=dates["end_date"],
        amount=plan["amount"],
        next_billing_date=dates["next_billing_date"],
        auto_renewal=False,
        created_at=now,
        updated_at=now,
        last_payment_date=now,
        restored_at=now,
        restored_by=current_user.id,
        restored_from_subscription_id=(previous_snapshot or {}).get("subscription_id") or (last_subscription or {}).get("id"),
        restored_from_plan_id=(previous_snapshot or {}).get("plan_id") or (last_subscription or {}).get("plan_id"),
        restored_from_plan_name=(previous_snapshot or {}).get("plan_name") or (last_subscription or {}).get("plan_name"),
    )

    await db.subscriptions.update_many(
        {"student_id": user_id, "status": {"$in": ["ACTIVE", "PENDING"]}},
        {"$set": {"status": "INACTIVE", "updated_at": now}},
    )
    await db.subscriptions.insert_one(restored_subscription.dict())

    if last_subscription:
        await store_previous_subscription_snapshot(
            user_id,
            last_subscription,
            source="admin_restore",
            action_by=current_user.id,
            reason=action.reason or f"Restored plan via {restore_option}",
        )

    admin_payment = PaymentRecord(
        transaction_id=restore_subscription_id,
        subscription_id=restore_subscription_id,
        student_id=user_id,
        plan_id=plan["id"],
        plan_name=plan["name"],
        billing_cycle=plan["billing_cycle"],
        amount=0,
        payment_type="subscription",
        status="SUCCESS",
        description=action.reason or "Subscription restored by admin",
        provider="admin",
        merchant_order_id=restore_subscription_id,
        provider_order_id=restore_subscription_id,
        provider_response={"source": "admin_restore"},
        paid_at=now,
    )
    await db.payments.insert_one(admin_payment.dict())

    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {"is_blocked": False},
            "$unset": {"blocked_reason": "", "blocked_at": "", "blocked_by": ""},
        },
    )

    return {
        "success": True,
        "subscription_id": restore_subscription_id,
        "restore_option": restore_option,
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "message": "Subscription restored successfully",
    }

# ============= NEW AI FUNCTIONS =============

async def analyze_quiz_result(student_id: str, quiz_id: str, attempt_id: str) -> QuizAnalysis:
    """Agentic AI workflow to analyze quiz results and provide insights"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Get quiz attempt details
        attempt = await db.quiz_attempts.find_one({"id": attempt_id})
        quiz = await db.quizzes.find_one({"id": quiz_id})
        
        if not attempt or not quiz:
            raise ValueError("Quiz attempt or quiz not found")
        
        # Get student's previous attempts for trend analysis
        previous_attempts = await db.quiz_attempts.find({
            "student_id": student_id,
            "completed_at": {"$lt": attempt["completed_at"]}
        }).sort("completed_at", -1).to_list(10)
        
        # Analyze wrong answers
        wrong_questions = []
        for q_idx, selected_option in attempt["answers"].items():
            if int(q_idx) < len(quiz["questions"]):
                question = quiz["questions"][int(q_idx)]
                if question["correct_answer"] != selected_option:
                    wrong_questions.append({
                        "question": question["question"],
                        "selected": question["options"][selected_option],
                        "correct": question["options"][question["correct_answer"]],
                        "explanation": question["explanation"]
                    })
        
        # Calculate trend
        scores = [att["percentage"] for att in previous_attempts[-5:]] + [attempt["percentage"]]
        trend = "improving" if len(scores) > 1 and scores[-1] > scores[-2] else "stable"
        if len(scores) >= 3:
            if all(scores[i] < scores[i+1] for i in range(len(scores)-2)):
                trend = "improving"
            elif all(scores[i] > scores[i+1] for i in range(len(scores)-2)):
                trend = "declining"
        
        # Generate AI analysis
        prompt = f"""Analyze this student's quiz performance:

Quiz: {quiz['title']} ({quiz['subject']})
Score: {attempt['percentage']:.1f}% ({attempt['score']}/{attempt['total_marks']})
Previous 5 scores: {[att['percentage'] for att in previous_attempts[:5]]}

Wrong Answers Analysis:
{json.dumps(wrong_questions, indent=2)}

Provide JSON analysis:
{{
  "performance_summary": "brief summary of performance",
  "key_insights": ["insight1", "insight2", "insight3"],
  "recommendations": ["action1", "action2", "action3"],
  "concept_gaps": ["concept1", "concept2"],
  "study_focus": ["topic1", "topic2", "topic3"]
}}"""

        response = model.generate_content(prompt)
        
        # Parse AI analysis
        try:
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
            else:
                analysis_data = {
                    "performance_summary": f"Scored {attempt['percentage']:.1f}% on {quiz['title']}",
                    "key_insights": ["Analysis completed", "Performance tracked"],
                    "recommendations": ["Review incorrect answers", "Practice similar questions"],
                    "concept_gaps": ["Review concepts"],
                    "study_focus": ["Continue practice"]
                }
        except:
            analysis_data = {
                "performance_summary": f"Scored {attempt['percentage']:.1f}% on {quiz['title']}",
                "key_insights": ["Analysis completed"],
                "recommendations": ["Review and practice"],
                "concept_gaps": ["General review needed"],
                "study_focus": ["Practice more questions"]
            }
        
        # Create quiz analysis record
        quiz_analysis = QuizAnalysis(
            student_id=student_id,
            quiz_id=quiz_id,
            attempt_id=attempt_id,
            analysis_data=analysis_data,
            insights=analysis_data.get("key_insights", []),
            recommendations=analysis_data.get("recommendations", []),
            performance_trend=trend
        )
        
        # Save analysis to database
        await db.quiz_analysis.insert_one(quiz_analysis.dict())
        
        return quiz_analysis
        
    except Exception as e:
        logging.error(f"Quiz analysis error: {e}")
        # Return basic analysis
        return QuizAnalysis(
            student_id=student_id,
            quiz_id=quiz_id,
            attempt_id=attempt_id,
            analysis_data={"error": "Analysis failed"},
            insights=["Quiz completed successfully"],
            recommendations=["Continue practicing"],
            performance_trend="stable"
        )

async def extract_text_from_pdf(file_content: bytes) -> List[str]:
    """Extract text from PDF file"""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        pages_text = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            pages_text.append(text)
        
        return pages_text
    except Exception as e:
        logging.error(f"PDF extraction error: {e}")
        return []

async def create_rag_embeddings(material_id: str, pages_text: List[str], upload_type: str = "teacher"):
    """Create embeddings for RAG system using Pinecone"""
    try:
        if not pinecone_index:
            logging.error("Pinecone index not available")
            return False
        
        # Create embeddings for each page
        for page_num, text in enumerate(pages_text):
            if text.strip():  # Only process non-empty pages
                # Generate embedding
                embedding = sentence_model.encode(text).tolist()
                
                # Create unique ID
                doc_id = f"{material_id}_page_{page_num}"
                
                # Upsert to Pinecone
                pinecone_index.upsert([
                    {
                        "id": doc_id,
                        "values": embedding,
                        "metadata": {
                            "material_id": material_id,
                            "page_number": page_num,
                            "text": text[:1000],  # Store first 1000 chars in metadata
                            "upload_type": upload_type,
                            "full_text": text
                        }
                    }
                ])
                
                # Store document record in MongoDB
                rag_doc = RAGDocument(
                    material_id=material_id,
                    content=text,
                    page_number=page_num,
                    embedding_id=doc_id
                )
                await db.rag_documents.insert_one(rag_doc.dict())
        
        return True
    except Exception as e:
        logging.error(f"RAG embedding error: {e}")
        return False

async def query_rag_system(
    question: str,
    subject: str = None,
    grade_level: str = None,
    material_filter: str = None,
    include_teacher_materials: bool = True,
    debug: bool = False,          # set True temporarily to get verbose prints
    include_values_for_debug: bool = False,  # set True to inspect stored vector lengths
    score_threshold: float = 0.3  # relaxed threshold
) -> str:
    """Query RAG system using Pinecone for course-related answers.
       Debug-friendly: set debug=True to print diagnostic info.
    """
    try:
        if not pinecone_index:
            return "RAG system not available. Please contact administrator."
        
        # --- 1) create query embedding and normalize it ---
        raw_q_emb = sentence_model.encode(question)
        # guard
        if raw_q_emb is None:
            if debug: print("❌ sentence_model returned None for query embedding")
            return "Failed to create query embedding."
        
        # convert to numpy and normalize (good for cosine sim)
        import numpy as np
        q_vec = np.array(raw_q_emb, dtype=float)
        norm = np.linalg.norm(q_vec)
        if norm == 0 or np.isnan(norm):
            if debug: print("❌ query embedding has zero or NaN norm:", norm)
            return "Failed to create a usable query embedding."
        q_vec = (q_vec / norm).tolist()
        
        if debug:
            print("🔷 QUERY EMBEDDING len:", len(q_vec))
            print("🔷 QUERY EMBEDDING sample:", q_vec[:6])
        
        # --- 2) prepare filter safely ---
        filter_dict = None
        if material_filter:
            # exact match on the metadata key you used during upsert
            filter_dict = {"material_id": {"$eq": material_filter}}
        elif include_teacher_materials:
            filter_dict = {"upload_type": {"$in": ["teacher", "student"]}}
        # else leave None (no filter)
        
        if debug:
            print("🔍 FILTER:", filter_dict)
        
        # --- 3) Query Pinecone (temporarily include values if debugging) ---
        query_kwargs = dict(
            vector=q_vec,
            top_k=8,
            include_metadata=True
        )
        if filter_dict:
            query_kwargs['filter'] = filter_dict
        if include_values_for_debug:
            query_kwargs['include_values'] = True
        
        results = pinecone_index.query(**query_kwargs)
        
        # Defensive: results may be None or have no matches
        matches = getattr(results, "matches", None) or results.get("matches") if isinstance(results, dict) else results.matches if results else []
        if debug:
            print("📦 matches found:", len(matches))
            # print each match's score + metadata summary
            for i, m in enumerate(matches):
                score = getattr(m, "score", None) or (m.get("score") if isinstance(m, dict) else None)
                meta = getattr(m, "metadata", None) or (m.get("metadata") if isinstance(m, dict) else None)
                values_len = getattr(m, "values", None)
                if values_len is not None:
                    try:
                        values_len = len(values_len)
                    except Exception:
                        values_len = "n/a"
                else:
                    values_len = "not included"
                print(f"  match[{i}] score={score} values_len={values_len} meta_keys={list(meta.keys()) if meta else None}")
        
        if not matches:
            # nothing found — provide informative message (and debug hints)
            msg = "I couldn't find relevant information in the uploaded materials."
            if debug:
                msg += " Debug hints: check index dimension, ensure embeddings were upserted as numeric lists, verify metadata keys and namespaces."
            return msg
        
        # --- 4) Build contexts: accept by score OR fallback to top-k ---
        contexts = []
        sources = []
        # first try collecting by threshold
        for m in matches:
            score = getattr(m, "score", None) or (m.get("score") if isinstance(m, dict) else None) or 0.0
            meta = getattr(m, "metadata", None) or (m.get("metadata") if isinstance(m, dict) else {})
            full_text = None
            # prefer 'full_text', then 'text' then 'content'
            for key in ("full_text", "text", "content"):
                if isinstance(meta, dict) and meta.get(key):
                    full_text = meta.get(key)
                    break
            if score >= score_threshold and full_text:
                contexts.append(full_text)
                sources.append(meta.get("upload_type", "unknown"))
        
        # if nothing passed threshold, fallback to top-k matches that have any text
        if not contexts:
            if debug: print("⚠️ No matches passed threshold; falling back to top-k matches")
            for m in matches[:6]:  # fallback: top 6
                meta = getattr(m, "metadata", None) or (m.get("metadata") if isinstance(m, dict) else {})
                full_text = None
                for key in ("full_text", "text", "content"):
                    if isinstance(meta, dict) and meta.get(key):
                        full_text = meta.get(key)
                        break
                if full_text:
                    contexts.append(full_text)
                    sources.append(meta.get("upload_type", "unknown"))
                if len(contexts) >= 6:
                    break
        
        if not contexts:
            # final fallback -> general AI answer
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""As an AI tutor, answer this student's question about {subject or 'academics'}:

Question: {question}

Provide a clear, educational answer appropriate for {grade_level or 'general'} level. Since no specific course materials were found, provide general knowledge and suggest the student ask their teacher for more specific information."""
            response = model.generate_content(prompt)
            return f"📚 **General AI Answer** (No specific course materials found):\n\n{response.text}\n\n💡 *Tip: Ask your teacher to upload course materials for more specific answers!*"
        
        # --- 5) Generate final answer with LLM using the collected contexts ---
        model = genai.GenerativeModel('gemini-2.5-flash')
        context_text = "\n\n".join(contexts[:6])  # combine up to 6 chunks
        sources_text = ", ".join(sorted(set(sources))[:3])
        llm_prompt = f"""Based on the following course materials, answer the student's question comprehensively:

Course Materials Context:
{context_text}

Student Question: {question}

Instructions:
1. Provide a clear, educational answer based primarily on the course materials
2. If the materials don't fully cover the question, supplement with relevant knowledge
3. Make the answer appropriate for {grade_level or 'general'} level in {subject or 'the subject'}
4. Be thorough but easy to understand
5. Include examples when helpful

Answer:"""
        response = model.generate_content(llm_prompt)
        return f"📖 **Answer from Course Materials** (Sources: {sources_text}):\n\n{response.text}"
    
    except Exception as e:
        logging.exception("RAG query error:")
        # Provide a plain message to client (not entire stack)
        return "I'm having trouble accessing the course materials right now. Please try again later."

async def summarize_notes(note_content: str, summary_type: str = "brief") -> str:
    """Summarize student notes using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        if summary_type == "brief":
            prompt = f"""Please create a brief summary of these student notes (2-3 bullet points):

Notes:
{note_content}

Summary:"""
        elif summary_type == "detailed":
            prompt = f"""Please create a detailed summary of these student notes with key concepts and important details:

Notes:
{note_content}

Detailed Summary:"""
        else:  # key_points
            prompt = f"""Extract and list the key points from these student notes:

Notes:
{note_content}

Key Points:"""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logging.error(f"Note summarization error: {e}")
        return "Failed to summarize notes. Please try again."

# ============= DYNAMIC QUIZ FUNCTIONS =============

async def generate_dynamic_quiz(request: DynamicQuizRequest) -> Dict[str, Any]:
    """Generate dynamic quiz using Gemini AI based on user inputs"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""Generate a {request.difficulty} difficulty quiz for {request.grade_level or 'Grade 8'} students.

Subject: {request.subject}
Topic: {request.topic}
Number of Questions: {request.num_questions}
Difficulty Level: {request.difficulty}

Please create exactly {request.num_questions} multiple choice questions. Each question should have 4 options (A, B, C, D) with only one correct answer.

Format your response as JSON:
{{
  "quiz_title": "Quiz title based on topic",
  "subject": "{request.subject}",
  "topic": "{request.topic}",
  "difficulty": "{request.difficulty}",
  "grade_level": "{request.grade_level}",
  "questions": [
    {{
      "question_number": 1,
      "question": "Question text here",
      "options": {{
        "A": "Option A text",
        "B": "Option B text", 
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A",
      "explanation": "Brief explanation of why this is correct"
    }}
  ]
}}

Make sure questions are appropriate for {request.difficulty} difficulty and {request.grade_level} level."""

        response = model.generate_content(prompt)
        
        # Parse the JSON response
        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            quiz_data = json.loads(json_match.group())
            quiz_data["id"] = str(uuid.uuid4())
            quiz_data["created_at"] = datetime.utcnow().isoformat()
            return quiz_data
        else:
            raise ValueError("Could not parse quiz JSON")
            
    except Exception as e:
        logging.error(f"Dynamic quiz generation error: {e}")
        # Return fallback quiz
        return {
            "id": str(uuid.uuid4()),
            "quiz_title": f"{request.topic} Quiz",
            "subject": request.subject,
            "topic": request.topic,
            "difficulty": request.difficulty,
            "grade_level": request.grade_level,
            "questions": [
                {
                    "question_number": 1,
                    "question": f"What is a key concept in {request.topic}?",
                    "options": {
                        "A": "Option A",
                        "B": "Option B", 
                        "C": "Option C",
                        "D": "Option D"
                    },
                    "correct_answer": "A",
                    "explanation": "This is the correct answer based on the topic."
                }
            ],
            "created_at": datetime.utcnow().isoformat()
        }

async def evaluate_quiz_with_gemini(quiz_data: Dict[str, Any], student_answers: Dict[str, str], student_name: str) -> QuizEvaluation:
    """Evaluate quiz performance using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Calculate basic score
        correct_count = 0
        total_questions = len(quiz_data["questions"])
        
        detailed_analysis = []
        for question in quiz_data["questions"]:
            q_num = str(question["question_number"])
            student_answer = student_answers.get(q_num, "")
            correct_answer = question["correct_answer"]
            
            is_correct = student_answer == correct_answer
            if is_correct:
                correct_count += 1
                
            detailed_analysis.append({
                "question": question["question"],
                "student_answer": student_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": question["explanation"]
            })
        
        percentage = (correct_count / total_questions) * 100
        
        # Generate AI evaluation
        analysis_prompt = f"""Analyze this quiz performance for student {student_name}:

Quiz Topic: {quiz_data["topic"]} ({quiz_data["subject"]})
Difficulty: {quiz_data["difficulty"]}
Score: {correct_count}/{total_questions} ({percentage:.1f}%)

Detailed Performance:
{json.dumps(detailed_analysis, indent=2)}

Please provide:
1. A comprehensive evaluation report (2-3 paragraphs)
2. List of 3-5 specific recommendations for improvement
3. List of 2-3 strengths demonstrated
4. List of 2-3 areas that need work

Format as JSON:
{{
  "evaluation_report": "Detailed performance analysis...",
  "recommendations": ["recommendation1", "recommendation2", ...],
  "strengths": ["strength1", "strength2", ...],
  "weaknesses": ["weakness1", "weakness2", ...]
}}"""

        ai_response = model.generate_content(analysis_prompt)
        
        # Parse AI evaluation
        import re
        json_match = re.search(r'\{.*\}', ai_response.text, re.DOTALL)
        if json_match:
            ai_eval = json.loads(json_match.group())
        else:
            ai_eval = {
                "evaluation_report": f"Student scored {percentage:.1f}% on the {quiz_data['topic']} quiz.",
                "recommendations": ["Review incorrect answers", "Practice more questions"],
                "strengths": ["Shows understanding of basic concepts"],
                "weaknesses": ["Needs improvement in specific areas"]
            }
        
        return QuizEvaluation(
            student_id="",  # Will be set by caller
            quiz_data=quiz_data,
            student_answers=student_answers,
            score=correct_count,
            total_questions=total_questions,
            percentage=percentage,
            evaluation_report=ai_eval["evaluation_report"],
            recommendations=ai_eval["recommendations"],
            strengths=ai_eval["strengths"],
            weaknesses=ai_eval["weaknesses"]
        )
        
    except Exception as e:
        logging.error(f"Quiz evaluation error: {e}")
        # Return basic evaluation
        return QuizEvaluation(
            student_id="",
            quiz_data=quiz_data,
            student_answers=student_answers,
            score=correct_count,
            total_questions=total_questions,
            percentage=percentage,
            evaluation_report=f"Quiz completed with {percentage:.1f}% score.",
            recommendations=["Review the questions and explanations"],
            strengths=["Completed the quiz"],
            weaknesses=["Areas for improvement identified"]
        )

# ============= EMAIL FUNCTIONS =============

async def send_quiz_report_email(email_report: EmailReport) -> bool:
    """Send formatted quiz report via email"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email_report.recipient_email
        msg['Subject'] = f"Quiz Report: {email_report.quiz_title}"
        
        # Create HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #10b981; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .score-box {{ background-color: #f0f9ff; border: 2px solid #0ea5e9; padding: 15px; margin: 15px 0; text-align: center; }}
                .recommendations {{ background-color: #fef3c7; padding: 15px; margin: 15px 0; }}
                .footer {{ background-color: #f9fafb; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎓 Edumate Quiz Report</h1>
                <h2>{email_report.quiz_title}</h2>
            </div>
            
            <div class="content">
                <h3>Dear {email_report.student_name},</h3>
                
                <p>Your quiz has been evaluated and here are your results:</p>
                
                <div class="score-box">
                    <h2>Your Score: {email_report.score}/{email_report.total_questions}</h2>
                    <h3>Percentage: {email_report.percentage:.1f}%</h3>
                    <p><strong>Performance Level: {"Excellent" if email_report.percentage >= 90 else "Good" if email_report.percentage >= 70 else "Needs Improvement"}</strong></p>
                </div>
                
                <h3>📊 Detailed Evaluation:</h3>
                <p>{email_report.evaluation_report}</p>
                
                <div class="recommendations">
                    <h3>💡 Recommendations for Improvement:</h3>
                    <ul>
        """
        
        for rec in email_report.recommendations:
            html_body += f"<li>{rec}</li>"
            
        html_body += f"""
                    </ul>
                </div>
                
                <h3>🎯 Next Steps:</h3>
                <ul>
                    <li>Review the topics where you scored lower</li>
                    <li>Practice similar questions to strengthen your understanding</li>
                    <li>Ask your teacher for help on challenging concepts</li>
                    <li>Take more quizzes to track your progress</li>
                </ul>
                
                <p>Keep up the great work and continue learning!</p>
                <p>— Edumate Team</p>
            </div>
            
            <div class="footer">
                <p>This report was generated by Edumate AI Learning Platform</p>
                <p>Contact your teacher if you have any questions about this report.</p>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, email_report.recipient_email, text)
        server.quit()
        
        logging.info(f"Quiz report sent to {email_report.recipient_email}")
        return True
        
    except Exception as e:
        logging.error(f"Email sending error: {e}")
        return False

# ============= WHATSAPP FUNCTIONS =============

async def send_whatsapp_message(phone_number: str, message: str) -> bool:
    """Send WhatsApp message via Twilio"""
    try:
        if not twilio_client:
            logging.error("Twilio client not initialized")
            return False
        
        # Ensure phone number is in WhatsApp format
        if not phone_number.startswith("whatsapp:"):
            phone_number = f"whatsapp:{phone_number}"
        
        message = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=phone_number
        )
        
        logging.info(f"WhatsApp message sent to {phone_number}: {message.sid}")
        return True
        
    except Exception as e:
        logging.error(f"WhatsApp message error: {e}")
        return False

async def process_whatsapp_message(phone_number: str, message_text: str) -> str:
    """Process incoming WhatsApp message and generate AI response"""
    try:
        # Clean phone number
        clean_phone = phone_number.replace("whatsapp:", "")
        
        # Check if user is registered
        whatsapp_user = await db.whatsapp_users.find_one({"phone_number": clean_phone})
        
        # Handle commands
        message_lower = message_text.lower().strip()
        
        # Registration process
        if not whatsapp_user or not whatsapp_user.get("registered", False):
            if message_lower.startswith("register"):
                return """🎓 Welcome to EduAgent WhatsApp AI Tutor!

To complete registration, please send your details in this format:
REGISTER [Your Name] [Your Email] [Student ID (optional)]

Example: 
REGISTER John Smith john@email.com

After registration, you can:
📚 Ask questions: Just type your question
🎯 Generate quiz: Type "quiz [subject] [topic]"  
📊 Get report: Type "report"

Start by sending your registration details!"""
            
            elif message_lower.startswith("register "):
                # Process registration
                parts = message_text.split(" ", 3)
                if len(parts) >= 3:
                    name = parts[1]
                    email = parts[2]
                    student_id = parts[3] if len(parts) > 3 else None
                    
                    # Find student by email if no ID provided
                    if not student_id:
                        student = await db.users.find_one({"email": email, "role": "student"})
                        if student:
                            student_id = student["id"]
                    
                    # Create or update WhatsApp user
                    whatsapp_user_data = WhatsAppUser(
                        phone_number=clean_phone,
                        student_id=student_id,
                        name=name,
                        registered=True
                    )
                    
                    await db.whatsapp_users.replace_one(
                        {"phone_number": clean_phone},
                        whatsapp_user_data.dict(),
                        upsert=True
                    )
                    
                    return f"""✅ Registration successful!

Welcome {name}! 🎉

You can now:
📚 **Ask Questions**: Just type any academic question
🎯 **Generate Quiz**: Type "quiz [subject] [topic] [difficulty]"
📊 **Get Report**: Type "report" for your progress
💡 **Study Help**: Ask for explanations, examples, or help with homework

Try asking: "What is photosynthesis?" or "quiz math algebra medium"

Happy learning! 🚀"""
                else:
                    return "❌ Registration format incorrect. Use: REGISTER [Name] [Email] [Student ID (optional)]"
            else:
                return """👋 Hello! I'm EduAgent AI Tutor.

Please register first by sending:
REGISTER [Your Name] [Your Email]

Example: REGISTER John Smith john@email.com"""
        
        # User is registered - process commands
        student_id = whatsapp_user.get("student_id")
        
        # Quiz generation command
        if message_lower.startswith("quiz "):
            parts = message_text.split(" ", 4)
            if len(parts) >= 3:
                subject = parts[1].title()
                topic = parts[2]
                difficulty = parts[3] if len(parts) > 3 else "medium"
                
                # Generate quiz
                quiz_request = DynamicQuizRequest(
                    subject=subject,
                    topic=topic,
                    difficulty=difficulty,
                    num_questions=5  # Shorter quiz for WhatsApp
                )
                
                quiz_data = await generate_dynamic_quiz(quiz_request)
                
                # Format quiz for WhatsApp
                quiz_text = f"🎯 **{quiz_data['quiz_title']}**\n"
                quiz_text += f"📚 Subject: {subject} | 📊 Difficulty: {difficulty}\n\n"
                
                for i, q in enumerate(quiz_data['questions'][:3], 1):  # Show only first 3 questions
                    quiz_text += f"**Q{i}:** {q['question']}\n"
                    for opt, text in q['options'].items():
                        quiz_text += f"{opt}) {text}\n"
                    quiz_text += "\n"
                
                quiz_text += "📱 Complete the full quiz on the EduAgent web platform for detailed analysis and email report!\n\n"
                quiz_text += f"🔗 Login at: learnmate-ai-12.preview.emergentagent.com"
                
                return quiz_text
            else:
                return "❌ Quiz format: quiz [subject] [topic] [difficulty]\nExample: quiz math algebra medium"
        
        # Report command
        elif message_lower in ["report", "progress"]:
            if student_id:
                try:
                    # Get recent quiz attempts
                    attempts = await db.quiz_evaluations.find({"student_id": student_id}).sort("created_at", -1).to_list(5)
                    
                    if attempts:
                        report = "📊 **Your Recent Progress**\n\n"
                        for attempt in attempts[:3]:
                            quiz_title = attempt.get("quiz_data", {}).get("quiz_title", "Quiz")
                            percentage = attempt.get("percentage", 0)
                            emoji = "🟢" if percentage >= 70 else "🟡" if percentage >= 50 else "🔴"
                            report += f"{emoji} {quiz_title}: {percentage:.1f}%\n"
                        
                        report += f"\n📈 **Latest Performance**: {attempts[0]['percentage']:.1f}%\n"
                        report += "🎯 Keep practicing to improve!\n\n"
                        report += "📧 Check your email for detailed reports after each quiz."
                        return report
                    else:
                        return "📊 No quiz attempts found yet.\n\nTake a quiz to see your progress!\nType: quiz [subject] [topic]"
                except Exception as e:
                    return "❌ Couldn't fetch your progress right now. Try again later."
            else:
                return "❌ Please complete registration to view reports."
        
        # Help command
        elif message_lower in ["help", "commands"]:
            return """🤖 **EduAgent WhatsApp Commands**

📚 **Ask Questions**: Just type any question
   Example: "What is photosynthesis?"

🎯 **Generate Quiz**: quiz [subject] [topic] [difficulty]
   Example: "quiz math algebra medium"

📊 **View Progress**: "report" or "progress"

💡 **Tips**:
   • Ask specific questions for better answers
   • Use the web platform for detailed features
   • Check email for quiz reports

🔗 Web Platform: learnmate-ai-12.preview.emergentagent.com

Just ask anything! 🚀"""
        
        # Regular question - use RAG system + Gemini
        else:
            # Query the RAG system
            answer = await query_rag_system(
                question=message_text,
                include_teacher_materials=True
            )
            
            # Format for WhatsApp (limit length)
            if len(answer) > 1500:
                answer = answer[:1500] + "...\n\n📱 Login to the web platform for complete answers!"
            
            return f"🤖 **AI Tutor Answer**:\n\n{answer}\n\n💡 Need more help? Just ask another question!"
    
    except Exception as e:
        logging.error(f"WhatsApp message processing error: {e}")
        return "❌ Sorry, I'm having trouble right now. Please try again later or use the web platform."

@api_router.get("/my-subscription")
async def get_my_subscription(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRoles.STUDENT:
        return {"has_subscription": False, "message": "Subscription applies to student accounts only"}

    access_status = current_user.student_access or await build_student_access_context(current_user.dict())
    subscription = access_status.get("subscription")

    return {
        "has_subscription": bool(subscription and subscription.get("status") == "ACTIVE"),
        "subscription": subscription,
        "previous_subscription": access_status.get("previous_subscription"),
        "access_status": access_status,
        "is_active": access_status.get("lifecycle_status") in {"MONTHLY_SUBSCRIPTION", "YEARLY_SUBSCRIPTION"},
        "lifecycle_status": access_status.get("lifecycle_status"),
        "expires_at": (subscription or {}).get("end_date"),
        "trial_end_at": access_status.get("trial_end_at"),
        "next_billing_date": access_status.get("next_billing_date"),
    }

@api_router.get("/payment-success")
async def payment_success_page(transaction_id: str = None):
    return {
        "message": "Payment completed successfully!",
        "transaction_id": transaction_id,
        "redirect_to": f"{CALLBACK_BASE_URL}?payment=success&transaction_id={transaction_id or ''}"
    }

@api_router.get("/payment-failure") 
async def payment_failure_page(transaction_id: str = None):
    return {
        "message": "Payment failed. Please try again.",
        "transaction_id": transaction_id,
        "redirect_to": f"{CALLBACK_BASE_URL}?payment=failed&transaction_id={transaction_id or ''}"
    }

# ============= FILE UPLOAD ROUTES =============

@api_router.post("/teacher/upload-material")
async def upload_study_material(
    file: UploadFile = File(...),
    subject: str = None,
    grade_level: str = None,
    description: str = None,
    current_user: User = Depends(get_current_user)
):
    """Upload study material files (PDF) for teachers"""
    try:
        if current_user.role != "teacher":
            raise HTTPException(status_code=403, detail="Teacher access required")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        
        # Create study material record
        study_material = StudyMaterial(
            filename=filename,
            original_filename=file.filename,
            file_type="pdf",
            file_size=file_size,
            uploaded_by=current_user.id,
            subject=subject or "General",
            grade_level=grade_level or "General",
            description=description or f"Study material: {file.filename}",
            file_path=f"/uploads/{filename}",
            is_processed=False
        )
        
        await db.study_materials.insert_one(study_material.dict())
        
        # Process PDF for RAG system
        pages_text = await extract_text_from_pdf(file_content)
        
        if pages_text:
            success = await create_rag_embeddings(study_material.id, pages_text, "teacher")
            if success:
                await db.study_materials.update_one(
                    {"id": study_material.id},
                    {"$set": {"is_processed": True}}
                )
        
        return {
            "success": True,
            "material_id": study_material.id,
            "message": f"Study material uploaded and processed successfully",
            "pages_processed": len(pages_text)
        }
        
    except Exception as e:
        logging.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@api_router.get("/teacher/my-materials")
async def get_teacher_materials(current_user: User = Depends(get_current_user)):
    """Get materials uploaded by teacher"""
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    
    try:
        materials = await db.study_materials.find({"uploaded_by": current_user.id}).to_list(100)
        materials = [fix_objectids(m) for m in materials]  # 👈 convert ObjectIds
        return {"materials": materials}
        
    except Exception as e:
        logging.error(f"Get materials error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= RAG SYSTEM ROUTES =============

@api_router.post("/rag/ask")
async def rag_question(
    query_request: RAGQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Ask questions based on uploaded course materials and AI knowledge"""
    try:
        # Query RAG system with teacher materials included
        answer = await query_rag_system(
            question=query_request.question,
            subject=query_request.subject,
            grade_level=query_request.grade_level,
            include_teacher_materials=True
        )
        
        # Save question for tracking
        question_record = Question(
            student_id=current_user.id,
            question=query_request.question,
            subject=query_request.subject or "General",
            answer=answer,
            answered_by="ENHANCED_RAG_AI"
        )
        
        await db.questions.insert_one(question_record.dict())
        
        return {
            "question": query_request.question,
            "answer": answer,
            "source": "course_materials_and_ai",
            "answered_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"RAG question error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/materials/available")
async def get_available_materials(current_user: User = Depends(get_current_user)):
    """Get available study materials for students"""
    try:
        # Get both teacher and student materials
        teacher_materials = await db.study_materials.find({"is_processed": True}).to_list(100)
        
        # If student, also get their personal PDFs
        student_pdfs = []
        if current_user.role == "student":
            student_pdfs = await db.student_pdfs.find({"student_id": current_user.id}).to_list(50)
        
        # Clean ObjectIds
        for material in teacher_materials:
            if "_id" in material:
                del material["_id"]
        
        for pdf in student_pdfs:
            if "_id" in pdf:
                del pdf["_id"]
        
        return {
            "teacher_materials": teacher_materials,
            "my_pdfs": student_pdfs,
            "total_materials": len(teacher_materials) + len(student_pdfs)
        }
        
    except Exception as e:
        logging.error(f"Get available materials error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/materials/available")
async def get_available_materials(current_user: User = Depends(get_current_user)):
    """Get available study materials"""
    try:
        materials = await db.study_materials.find({"is_processed": True}).to_list(100)
        return {"materials": materials}
        
    except Exception as e:
        logging.error(f"Get available materials error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= NOTES ROUTES =============

@api_router.post("/notes/create")
async def create_note(
    note_data: NoteCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new note"""
    try:
        note = StudentNote(
            student_id=current_user.id,
            title=note_data.title,
            content=note_data.content,
            subject=note_data.subject,
            tags=note_data.tags
        )
        
        await db.student_notes.insert_one(note.dict())
        
        return {"success": True, "id": note.id, "message": "Note created successfully"}
        
    except Exception as e:
        logging.error(f"Note creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/notes/my-notes")
async def get_my_notes(current_user: User = Depends(get_current_user)):
    """Get all notes for current user"""
    try:
        notes = await db.student_notes.find({"student_id": current_user.id}).sort("updated_at", -1).to_list(100)
        
        # Clean ObjectId from notes
        clean_notes = []
        for note in notes:
            if "_id" in note:
                del note["_id"]
            clean_notes.append(note)
        
        return {"notes": clean_notes}
        
    except Exception as e:
        logging.error(f"Get notes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/notes/{note_id}")
async def update_note(
    note_id: str,
    note_data: NoteCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update a note"""
    try:
        result = await db.student_notes.update_one(
            {"id": note_id, "student_id": current_user.id},
            {
                "$set": {
                    "title": note_data.title,
                    "content": note_data.content,
                    "subject": note_data.subject,
                    "tags": note_data.tags,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Note not found")
        
        return {"success": True, "message": "Note updated successfully"}
        
    except Exception as e:
        logging.error(f"Note update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a note"""
    try:
        result = await db.student_notes.delete_one(
            {"id": note_id, "student_id": current_user.id}
        )
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Note not found")
        
        return {"success": True, "message": "Note deleted successfully"}
        
    except Exception as e:
        logging.error(f"Note deletion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/notes/summarize")
async def summarize_note(
    summary_request: NoteSummaryRequest,
    current_user: User = Depends(get_current_user)
):
    """Summarize notes using AI"""
    try:
        summary = await summarize_notes(
            summary_request.note_content,
            summary_request.summary_type
        )
        
        return {
            "original_length": len(summary_request.note_content),
            "summary": summary,
            "summary_type": summary_request.summary_type,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Note summarization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= DYNAMIC QUIZ ROUTES =============

@api_router.post("/quiz/generate-dynamic")
async def create_dynamic_quiz(
    quiz_request: DynamicQuizRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate dynamic quiz based on user inputs"""
    try:
        # Generate quiz using Gemini
        quiz_data = await generate_dynamic_quiz(quiz_request)
        
        # Save quiz to database (optional, for tracking)
        quiz_record = {
            "id": quiz_data["id"],
            "title": quiz_data["quiz_title"],
            "subject": quiz_data["subject"],
            "topic": quiz_data["topic"],
            "difficulty": quiz_data["difficulty"],
            "grade_level": quiz_data["grade_level"],
            "questions": quiz_data["questions"],
            "created_by": current_user.id,
            "created_at": datetime.utcnow(),
            "quiz_type": "dynamic"
        }
        
        await db.dynamic_quizzes.insert_one(quiz_record)
        
        return {
            "success": True,
            "quiz": quiz_data,
            "message": f"Dynamic quiz generated with {len(quiz_data['questions'])} questions"
        }
        
    except Exception as e:
        logging.error(f"Dynamic quiz creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/quiz/submit-dynamic/{quiz_id}")
async def submit_dynamic_quiz(
    quiz_id: str,
    student_answers: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """Submit dynamic quiz and get AI evaluation with email report"""
    try:
        # Get quiz data
        quiz_record = await db.dynamic_quizzes.find_one({"id": quiz_id})
        if not quiz_record:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Clean ObjectId from quiz record
        if "_id" in quiz_record:
            del quiz_record["_id"]
        
        # Evaluate with Gemini AI
        evaluation = await evaluate_quiz_with_gemini(
            quiz_record, 
            student_answers, 
            current_user.name
        )
        evaluation.student_id = current_user.id
        
        # Save evaluation to database
        eval_record = evaluation.dict()
        eval_record["quiz_id"] = quiz_id
        eval_record["created_at"] = datetime.utcnow()
        
        await db.quiz_evaluations.insert_one(eval_record)
        
        # Send email report if student has email
        if hasattr(current_user, 'email') and current_user.email:
            email_report = EmailReport(
                recipient_email=current_user.email,
                student_name=current_user.name,
                quiz_title=quiz_record["title"],
                score=evaluation.score,
                total_questions=evaluation.total_questions,
                percentage=evaluation.percentage,
                evaluation_report=evaluation.evaluation_report,
                recommendations=evaluation.recommendations
            )
            
            email_sent = await send_quiz_report_email(email_report)
            
            return {
                "success": True,
                "evaluation": evaluation.dict(),
                "email_sent": email_sent,
                "message": "Quiz evaluated successfully" + (" and report sent to your email" if email_sent else "")
            }
        else:
            return {
                "success": True,
                "evaluation": evaluation.dict(),
                "email_sent": False,
                "message": "Quiz evaluated successfully. Add email to your profile to receive reports."
            }
        
    except Exception as e:
        logging.error(f"Dynamic quiz submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/quiz/my-dynamic-attempts")
async def get_my_dynamic_quiz_attempts(current_user: User = Depends(get_current_user)):
    """Get student's dynamic quiz attempts and evaluations"""
    try:
        evaluations = await db.quiz_evaluations.find({"student_id": current_user.id}).sort("created_at", -1).to_list(50)
        
        # Clean ObjectIds
        for eval in evaluations:
            if "_id" in eval:
                del eval["_id"]
        
        return {"evaluations": evaluations}
        
    except Exception as e:
        logging.error(f"Quiz attempts retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= STUDENT PDF UPLOAD ROUTES =============

@api_router.post("/student/upload-pdf")
async def upload_student_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Allow students to upload their own PDFs for RAG"""
    try:
        if current_user.role != "student":
            raise HTTPException(status_code=403, detail="Student access required")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Generate unique ID
        upload_id = str(uuid.uuid4())
        
        # Extract text from PDF
        pages_text = await extract_text_from_pdf(file_content)
        
        if not pages_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Store PDF record
        pdf_record = StudentPDFUpload(
            student_id=current_user.id,
            filename=f"{upload_id}_{file.filename}",
            original_filename=file.filename,
            file_size=file_size
        )
        
        await db.student_pdfs.insert_one(pdf_record.dict())
        
        # Create embeddings with student-specific material ID
        material_id = f"student_{current_user.id}_{upload_id}"
        success = await create_rag_embeddings(material_id, pages_text, "student")
        
        if success:
            return {
                "success": True,
                "material_id": material_id,
                "filename": file.filename,
                "pages_processed": len(pages_text),
                "message": "PDF uploaded and processed successfully! You can now ask questions about this document."
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process PDF for Q&A")
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Student PDF upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/student/my-pdfs")
async def get_my_uploaded_pdfs(current_user: User = Depends(get_current_user)):
    """Get student's uploaded PDFs"""
    try:
        if current_user.role != "student":
            raise HTTPException(status_code=403, detail="Student access required")
        
        pdfs = await db.student_pdfs.find({"student_id": current_user.id}).sort("created_at", -1).to_list(50)
        
        # Clean ObjectIds
        for pdf in pdfs:
            if "_id" in pdf:
                del pdf["_id"]
        
        return {"pdfs": pdfs}
        
    except Exception as e:
        logging.error(f"Student PDFs retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/student/ask-my-pdf")
async def ask_question_to_my_pdf(
    material_id: str,
    question: str,
    current_user: User = Depends(get_current_user)
):
    """Ask questions specifically to student's uploaded PDF"""
    try:
        if current_user.role != "student":
            raise HTTPException(status_code=403, detail="Student access required")
        
        # Verify the material belongs to the student
        if not material_id.startswith(f"student_{current_user.id}_"):
            raise HTTPException(status_code=403, detail="You can only query your own uploaded documents")
        
        # Query RAG system with material filter
        answer = await query_rag_system(
            question=question,
            material_filter=material_id
        )
        
        # Save question for tracking
        question_record = Question(
            student_id=current_user.id,
            question=question,
            subject="Personal Document",
            answer=answer,
            answered_by="PDF_RAG_AI"
        )
        
        await db.questions.insert_one(question_record.dict())
        
        return {
            "question": question,
            "answer": answer,
            "source": "your_uploaded_document",
            "material_id": material_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Student PDF query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= WHATSAPP ROUTES =============

@api_router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """Handle WhatsApp webhook from Twilio"""
    try:
        form_data = await request.form()
        
        # Extract Twilio webhook data
        from_number = form_data.get('From', '')
        message_body = form_data.get('Body', '')
        message_sid = form_data.get('MessageSid', '')
        
        if not from_number or not message_body:
            return {"status": "error", "message": "Missing required fields"}
        
        logging.info(f"WhatsApp message received from {from_number}: {message_body}")
        
        # Store incoming message
        whatsapp_msg = WhatsAppMessage(
            phone_number=from_number,
            message_text=message_body,
            message_type="incoming"
        )
        
        await db.whatsapp_messages.insert_one(whatsapp_msg.dict())
        
        # Process message and get AI response
        ai_response = await process_whatsapp_message(from_number, message_body)
        
        # Send response via WhatsApp
        response_sent = await send_whatsapp_message(from_number, ai_response)
        
        # Store outgoing message
        if response_sent:
            response_msg = WhatsAppMessage(
                phone_number=from_number,
                message_text=ai_response,
                message_type="outgoing",
                response_sent=True
            )
            await db.whatsapp_messages.insert_one(response_msg.dict())
        
        return {"status": "success", "response_sent": response_sent}
        
    except Exception as e:
        logging.error(f"WhatsApp webhook error: {e}")
        return {"status": "error", "message": str(e)}

@api_router.get("/whatsapp/users")
async def get_whatsapp_users(current_user: User = Depends(get_current_user)):
    """Get WhatsApp users (admin only)"""
    try:
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(status_code=403, detail="Admin or teacher access required")
        
        users = await db.whatsapp_users.find({}).to_list(100)
        
        # Clean ObjectIds
        for user in users:
            if "_id" in user:
                del user["_id"]
        
        return {"whatsapp_users": users}
        
    except Exception as e:
        logging.error(f"WhatsApp users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/whatsapp/messages")
async def get_whatsapp_messages(
    phone_number: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get WhatsApp message history"""
    try:
        if current_user.role not in ["teacher", "admin"]:
            raise HTTPException(status_code=403, detail="Admin or teacher access required")
        
        query = {}
        if phone_number:
            query["phone_number"] = phone_number
        
        messages = await db.whatsapp_messages.find(query).sort("created_at", -1).to_list(100)
        
        # Clean ObjectIds
        for msg in messages:
            if "_id" in msg:
                del msg["_id"]
        
        return {"messages": messages}
        
    except Exception as e:
        logging.error(f"WhatsApp messages error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= QUIZ ANALYSIS ROUTES =============

@api_router.get("/quiz/analysis/{attempt_id}")
async def get_quiz_analysis(
    attempt_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get AI analysis for quiz attempt"""
    try:
        analysis = await db.quiz_analysis.find_one({"attempt_id": attempt_id})
        
        if not analysis:
            # Get attempt details to create analysis
            attempt = await db.quiz_attempts.find_one({"id": attempt_id})
            if not attempt:
                raise HTTPException(status_code=404, detail="Quiz attempt not found")
            
            # Generate analysis
            quiz_analysis = await analyze_quiz_result(
                attempt["student_id"],
                attempt["quiz_id"],
                attempt_id
            )
            analysis = quiz_analysis.dict()
        
        # Clean ObjectId from response
        if isinstance(analysis, dict) and "_id" in analysis:
            del analysis["_id"]
        
        return analysis
        
    except Exception as e:
        logging.error(f"Quiz analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= STUDENT PROFILE ROUTES =============

@api_router.get("/student/profile")
async def get_student_profile(current_user: User = Depends(get_current_user)):
    """Get student profile"""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    
    try:
        profile = await db.student_profiles.find_one({"student_id": current_user.id})
        
        if profile and "_id" in profile:
            del profile["_id"]

        access_status = current_user.student_access or await build_student_access_context(current_user.dict())
        subscription = access_status.get("subscription")

        return {
            "profile": profile,
            "billing": {
                "plan_name": (subscription or {}).get("plan_name"),
                "plan_id": (subscription or {}).get("plan_id"),
                "billing_cycle": (subscription or {}).get("billing_cycle"),
                "amount": (subscription or {}).get("amount"),
                "subscription_status": access_status.get("status"),
                "lifecycle_status": access_status.get("lifecycle_status"),
                "next_billing_date": access_status.get("next_billing_date"),
                "trial_end_at": access_status.get("trial_end_at"),
                "trial_days_remaining": access_status.get("trial_days_remaining"),
                "previous_subscription": access_status.get("previous_subscription"),
                "is_blocked": access_status.get("is_blocked"),
                "message": access_status.get("message"),
            },
        }
        
    except Exception as e:
        logging.error(f"Profile fetch error: {e}")
        return {"profile": None, "billing": None}

@api_router.post("/student/profile")
async def save_student_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Save student profile"""
    try:
        if current_user.role != "student":
            raise HTTPException(status_code=403, detail="Student access required")
        
        # Add student ID and timestamps
        profile_data["student_id"] = current_user.id
        profile_data["updated_at"] = datetime.utcnow()
        
        # Upsert profile
        await db.student_profiles.replace_one(
            {"student_id": current_user.id},
            profile_data,
            upsert=True
        )
        
        return {"success": True, "profile_id": current_user.id, "message": "Profile saved successfully"}
        
    except Exception as e:
        logging.error(f"Profile save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= PERSONALIZED LEARNING ROUTES =============

@api_router.get("/learning-path")
async def get_learning_path(current_user: User = Depends(get_current_user)):
    """Get personalized learning path for student"""
    try:
        # Check for existing learning path
        existing_path = await db.learning_paths.find_one({"student_id": current_user.id})
        
        if existing_path:
            return LearningPath(**existing_path)
        
        # Generate new learning path
        learning_path = await generate_personalized_learning_path(current_user.id)
        
        # Save to database
        await db.learning_paths.insert_one(learning_path.dict())
        
        return learning_path
        
    except Exception as e:
        logging.error(f"Learning path error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate learning path: {str(e)}")

class LearningProgressUpdate(BaseModel):
    completed_topic: str

@api_router.post("/update-learning-progress")
async def update_learning_progress(
    progress_data: LearningProgressUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update learning progress when student completes a topic"""
    try:
        completed_topic = progress_data.completed_topic
        # Update learning path
        await db.learning_paths.update_one(
            {"student_id": current_user.id},
            {
                "$addToSet": {"completed_topics": completed_topic},
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        # Generate new recommendations
        learning_path = await generate_personalized_learning_path(current_user.id)
        
        # Update with new recommendations
        await db.learning_paths.update_one(
            {"student_id": current_user.id},
            {"$set": learning_path.dict()}
        )
        
        return {"message": "Learning progress updated", "next_recommendations": learning_path.next_recommendations}
        
    except Exception as e:
        logging.error(f"Learning progress update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/learning-insights")
async def get_learning_insights(current_user: User = Depends(get_current_user)):
    """Get AI-generated learning insights for student"""
    try:
        # Get recent performance
        recent_attempts = await db.quiz_attempts.find({"student_id": current_user.id}).sort("completed_at", -1).to_list(10)
        
        if not recent_attempts:
            return {"insights": [], "message": "Take some quizzes to get personalized insights"}
        
        # Generate insights
        insights = []
        
        # Performance trend insight
        if len(recent_attempts) >= 3:
            recent_scores = [attempt["percentage"] for attempt in recent_attempts[:3]]
            if all(recent_scores[i] >= recent_scores[i+1] for i in range(len(recent_scores)-1)):
                insights.append({
                    "type": "achievement",
                    "title": "Improving Performance!",
                    "description": "Your quiz scores are consistently improving. Keep up the great work!",
                    "priority": "high"
                })
        
        # Subject strength insight
        subject_performance = {}
        for attempt in recent_attempts:
            quiz = await db.quizzes.find_one({"id": attempt["quiz_id"]})
            if quiz:
                subject = quiz["subject"]
                if subject not in subject_performance:
                    subject_performance[subject] = []
                subject_performance[subject].append(attempt["percentage"])
        
        for subject, scores in subject_performance.items():
            avg_score = sum(scores) / len(scores)
            if avg_score >= 85:
                insights.append({
                    "type": "performance",
                    "title": f"Strong in {subject}",
                    "description": f"You're excelling in {subject} with an average of {avg_score:.1f}%!",
                    "priority": "medium"
                })
            elif avg_score < 60:
                insights.append({
                    "type": "recommendation",
                    "title": f"Focus on {subject}",
                    "description": f"Consider spending more time on {subject}. Practice makes perfect!",
                    "priority": "high",
                    "action_required": True
                })
        
        return {"insights": insights}
        
    except Exception as e:
        logging.error(f"Learning insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= PARENT PROGRESS ROUTES =============
from bson import ObjectId, errors as bson_errors
def to_objectid(id_value):
    """Convert hex string or ObjectId to ObjectId, or raise HTTPException(400)."""
    if isinstance(id_value, ObjectId):
        return id_value
    try:
        return ObjectId(id_value)
    except (bson_errors.InvalidId, TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid id: {id_value}")
# Sample generate_progress_report (implement fully based on your data)
async def generate_progress_report_for_parent(student_id: str, parent_id: str):
    # normalize student_id to ObjectId
    student_oid = to_objectid(student_id)
    student = await db.users.find_one({"_id": student_oid})
    if not student or student.get("parent_id") != parent_id:
        # use HTTPException so caller can send 403
        raise HTTPException(status_code=403, detail="Access denied to this student")

    quizzes = await db.quizzes.find({"student_id": str(student_oid)}).to_list(100)
    total_quizzes = len(quizzes)
    average_score = sum(q.get("score", 0) for q in quizzes) / total_quizzes if total_quizzes else 0
    total_questions_asked = sum(q.get("questions_asked", 0) for q in quizzes)

    # Ensure overall_performance always present
    return {
        "student_info": {"name": student["name"], "email": student["email"]},
        "overall_performance": {
            "total_quizzes": total_quizzes,
            "average_score": round(average_score, 2),
            "total_questions_asked": total_questions_asked,
            "performance_trend": "improving" if average_score > 70 else "stable"
        },
        "subject_performance": {},
        "ai_insights": "Your child is improving in math but needs focus on science.",
        "learning_path": {
            "current_level": "Intermediate",
            "strong_areas": ["Math"],
            "weak_areas": ["Science"]
        }
    }


# Sample get_student_progress (for dashboard)
async def get_student_progress_for_parent(student_id: str, parent_id: str):
    # Reuse generate_progress_report_for_parent which handles auth and ObjectId conversion
    report = await generate_progress_report_for_parent(student_id, parent_id)

    overall = report.get("overall_performance", {})
    return {
        "average_score": overall.get("average_score", 0),
        "total_quizzes": overall.get("total_quizzes", 0),
        "total_questions_asked": overall.get("total_questions_asked", 0),
        "subject_breakdown": report.get("subject_performance", {})
    }


# New Endpoint: Link Child
@api_router.post("/parent/link-child")
async def link_child(
    child_data: dict,  # {email: str, password: str}
    current_user: User = Depends(get_current_user)
):
    """Link a child to the parent account"""
    try:
        if current_user.role != "parent":
            raise HTTPException(status_code=403, detail="Parent access required")
        
        email = child_data.get("email")
        password = child_data.get("password")
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required")
        
        # Find the student by email
        student_doc = await db.users.find_one({"email": email, "role": "student"})
        if not student_doc:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Verify password using your verify_password function
        if not verify_password(password, student_doc["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        student_id = str(student_doc["_id"])
        
        # Check if already linked (student has parent_id or parent has student in list)
        if student_doc.get("parent_id") or student_id in (current_user.students or []):
            raise HTTPException(status_code=400, detail="Child already linked")
        
        # Link: Set student's parent_id and add to parent's students list
        await db.users.update_one(
            {"_id": student_doc["_id"]},
            {"$set": {"parent_id": str(current_user.id)}}
        )
        await db.users.update_one(
            {"id": current_user.id},
            {"$push": {"students": student_id}}
        )
        
        return {"message": "Child linked successfully", "student_id": student_id}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Link child error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Updated: Get Linked Students

@api_router.get("/parent/students")
async def get_linked_students(current_user: User = Depends(get_current_user)):
    """Get students and related info linked to parent account"""
    try:
        if current_user.role != "parent":
            raise HTTPException(status_code=403, detail="Parent access required")
        
        # Fetch students linked to the current parent
        students_docs = await db.users.find({"parent_id": str(current_user.id)}).to_list(100)

        students = []
        student_progress = []

        for doc in students_docs:
            student = {
                "_id": str(doc["_id"]),
                "id": doc.get("id"),
                "email": doc.get("email"),
                "name": doc.get("name"),
                "role": doc.get("role"),
                "phone": doc.get("phone"),
                "created_at": doc.get("created_at"),
                "is_verified": doc.get("is_verified"),
                "is_active": doc.get("is_active"),
                "students": doc.get("students", []),
                "classes": doc.get("classes", []),
                "parent_id": doc.get("parent_id"),
            }
            students.append(student)

            # TODO: Add logic to compute or fetch progress data
            # For now, add empty progress placeholders as in dashboard
            progress = {
                "average_score": 0,
                "total_quizzes": 0,
                "total_questions_asked": 0,
                "subject_breakdown": {}
            }
            student_progress.append({
                "student": student,
                "progress": progress
            })
        
        return {
            "user": {
                "email": current_user.email,
                "name": current_user.name,
                "role": current_user.role,
                "id": current_user.id,
                "created_at": current_user.created_at,
                "is_verified": current_user.is_verified,
                "is_active": current_user.is_active,
                "students": [str(s["_id"]) for s in students_docs],
                "classes": current_user.classes,
            },
            "students": students,
            "student_progress": student_progress
        }
        
    except Exception as e:
        logging.error(f"Linked students error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Updated: Get Progress Report
@api_router.get("/parent/progress-report/{student_id}")
async def get_student_progress_report(student_id: str, current_user: User = Depends(get_current_user)):
    try:
        if current_user.role != "parent":
            raise HTTPException(status_code=403, detail="Parent access required")

        # verify student linked to this parent using ObjectId
        student_oid = to_objectid(student_id)
        student = await db.users.find_one({"_id": student_oid, "parent_id": str(current_user.id)})
        if not student:
            raise HTTPException(status_code=403, detail="Access denied to this student")

        report = await generate_progress_report_for_parent(student_id, str(current_user.id))
        return report

    except HTTPException:
        # re-raise so FastAPI sends correct status code
        raise
    except Exception as e:
        logging.error(f"Progress report error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Updated: Get Parent Dashboard
@api_router.get("/dashboard/parent")
async def get_parent_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRoles.PARENT:
        raise HTTPException(status_code=403, detail="Parent access required")

    students_docs = await db.users.find({"parent_id": str(current_user.id)}).to_list(100)
    students = [fix_objectids(s) for s in students_docs]

    student_progress = []
    for student in students_docs:
        student_id_str = str(student["_id"])   # ensure string hex
        progress = await get_student_progress_for_parent(student_id_str, str(current_user.id))
        student_progress.append({
            "student": fix_objectids(student),
            "progress": progress
        })

    return {
        "user": fix_objectids(current_user.dict() if hasattr(current_user, "dict") else current_user),
        "students": students,
        "student_progress": student_progress
    }

# ============= GENERAL ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "EduMate API - AI Powered Educational Platform with Payment Gateway"}

@api_router.get("/subjects")
async def get_subjects():
    return {
        "subjects": [
            "Mathematics", "Science", "English", "History", 
            "Geography", "Physics", "Chemistry", "Biology",
            "Computer Science", "Economics", "Psychology"
        ]
    }

@api_router.get("/grade-levels")
async def get_grade_levels():
    return {
        "grade_levels": [
            "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5",
            "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10",
            "Grade 11", "Grade 12", "University Level"
        ]
    }

# Include the router in the main app
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_tasks():
    await ensure_admin_user_exists()
    await db.users.create_index("email")
    await db.users.create_index("role")
    await db.users.create_index("is_blocked")
    await db.users.create_index([("role", 1), ("trial_end_at", 1)])
    await db.users.create_index("student_status")
    await db.subscriptions.create_index([("student_id", 1), ("status", 1), ("end_date", -1)])
    await db.subscriptions.create_index([("student_id", 1), ("created_at", -1)])
    await db.subscriptions.create_index([("status", 1), ("billing_cycle", 1), ("end_date", -1)])
    await db.subscriptions.create_index("id")
    await db.payments.create_index("transaction_id")
    await db.payments.create_index("subscription_id")
    await db.payments.create_index([("status", 1), ("paid_at", -1)])

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

