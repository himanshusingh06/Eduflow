from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
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
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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

# AI Integration
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Initialize vector database and sentence transformer
chroma_client = chromadb.Client()
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET") 
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
CALLBACK_BASE_URL = os.environ.get("CALLBACK_BASE_URL")

# Create the main app
app = FastAPI(title="EduAgent - AI Powered Educational Platform")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ============= MODELS =============

# User Roles Constants
class UserRoles:
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"

class UserBase(BaseModel):
    email: str
    name: str
    role: str  # student, teacher, parent
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
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
    monthly_amount: int  # Amount in paise (Rs 1000 = 100000 paise)
    features: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentRequest(BaseModel):
    student_id: str
    amount: int  # Amount in paise
    description: str
    payment_type: str = "one_time"  # one_time, subscription

class SubscriptionRequest(BaseModel):
    student_id: str
    plan_id: str
    duration_months: int = 1

class PaymentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str
    student_id: str
    amount: int
    payment_type: str  # one_time, subscription
    status: str  # INITIATED, SUCCESS, FAILED, PENDING
    description: str
    phonepe_order_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    plan_id: str
    status: str  # ACTIVE, INACTIVE, EXPIRED, PENDING
    start_date: datetime
    end_date: datetime
    monthly_amount: int
    auto_renewal: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_payment_date: Optional[datetime] = None

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

# ============= UTILITY FUNCTIONS =============

def hash_password(password: str) -> str:
    # Using SHA256 with salt for password hashing
    salted_password = password + PASSWORD_SALT
    return hashlib.sha256(salted_password.encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Verify password by hashing the plain password and comparing
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + JWT_EXPIRATION_TIME
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user)

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

# ============= RAZORPAY INTEGRATION =============

import razorpay
import hmac
import hashlib

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay payment signature"""
    try:
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False

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

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        **user_data.dict(exclude={"password"}),
        id=str(uuid.uuid4())
    )
    
    # Hash password and store
    user_dict = user.dict()
    user_dict["password"] = hash_password(user_data.password)
    
    await db.users.insert_one(user_dict)
    
    # Create access token
    access_token = create_access_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    # Find user
    user_doc = await db.users.find_one({"email": login_data.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(login_data.password, user_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
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

@api_router.get("/quiz/list", response_model=List[Quiz])
async def get_quizzes(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if subject:
        query["subject"] = subject
    if current_user.role == "teacher":
        query["created_by"] = current_user.id
        
    quizzes = await db.quizzes.find(query).to_list(100)
    return [Quiz(**quiz) for quiz in quizzes]

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

@api_router.get("/dashboard/student")
async def get_student_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    
    # Get recent activities
    recent_quizzes = await db.quiz_attempts.find({"student_id": current_user.id}).sort("completed_at", -1).to_list(5)
    recent_questions = await db.questions.find({"student_id": current_user.id}).sort("created_at", -1).to_list(5)
    
    # Get available content
    available_content = await db.study_content.find({}).sort("created_at", -1).to_list(10)
    available_quizzes = await db.quizzes.find({}).sort("created_at", -1).to_list(10)
    
    return {
        "user": current_user,
        "recent_quiz_attempts": recent_quizzes,
        "recent_questions": recent_questions,
        "available_content": available_content,
        "available_quizzes": available_quizzes,
        "quick_stats": {
            "total_quizzes_taken": len(await db.quiz_attempts.find({"student_id": current_user.id}).to_list(1000)),
            "questions_asked": len(await db.questions.find({"student_id": current_user.id}).to_list(1000))
        }
    }

@api_router.get("/dashboard/teacher")
async def get_teacher_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    
    # Get created content
    my_content = await db.study_content.find({"created_by": current_user.id}).sort("created_at", -1).to_list(100)
    my_quizzes = await db.quizzes.find({"created_by": current_user.id}).sort("created_at", -1).to_list(100)
    
    # Get student activities on my content
    my_quiz_ids = [quiz["id"] for quiz in my_quizzes]
    quiz_attempts = await db.quiz_attempts.find({"quiz_id": {"$in": my_quiz_ids}}).sort("completed_at", -1).to_list(100)
    
    return {
        "user": current_user,
        "my_content": my_content,
        "my_quizzes": my_quizzes,
        "recent_quiz_attempts": quiz_attempts,
        "stats": {
            "total_content_created": len(my_content),
            "total_quizzes_created": len(my_quizzes),
            "total_student_attempts": len(quiz_attempts)
        }
    }

@api_router.get("/dashboard/parent")
async def get_parent_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Parent access required")
    
    # Get linked students (simplified - in real app, would have proper linking)
    students = await db.users.find({"role": "student"}).to_list(100)  # TODO: Add proper parent-child linking
    
    # Get progress for all students (simplified)
    student_progress = []
    for student in students[:5]:  # Limit for demo
        progress = await get_student_progress(student["id"], current_user)
        student_progress.append({"student": student, "progress": progress})
    
    return {
        "user": current_user,
        "students": students[:5],  # Demo data
        "student_progress": student_progress
    }

# ============= PAYMENT ROUTES =============

@api_router.get("/subscription-plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    plans = [
        {
            "id": "monthly_premium",
            "name": "Monthly Premium Access",
            "description": "Full access to all courses, quizzes, and AI tutoring",
            "monthly_amount": 100000,  # Rs 1000 in paise
            "price_display": "₹1,000/month",
            "features": [
                "Unlimited access to all courses",
                "Personalized AI tutoring",
                "Advanced quiz analytics", 
                "Progress tracking",
                "Priority support"
            ],
            "is_active": True
        }
    ]
    return {"plans": plans}

@api_router.post("/create-order")
async def create_razorpay_order(
    payment_request: PaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a Razorpay order for payment"""
    try:
        # Generate transaction ID
        transaction_id = f"PAY_{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        # Create Razorpay order
        order_data = {
            "amount": payment_request.amount,  # Amount in paise
            "currency": "INR",
            "receipt": transaction_id,
            "notes": {
                "student_id": current_user.id,
                "description": payment_request.description,
                "payment_type": payment_request.payment_type
            }
        }
        
        razorpay_order = razorpay_client.order.create(order_data)
        
        # Store payment record
        payment_record = PaymentRecord(
            transaction_id=transaction_id,
            student_id=current_user.id,
            amount=payment_request.amount,
            payment_type=payment_request.payment_type,
            status="CREATED",
            description=payment_request.description,
            phonepe_order_id=razorpay_order["id"]
        )
        
        await db.payments.insert_one(payment_record.dict())
        
        return {
            "success": True,
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": RAZORPAY_KEY_ID,
            "transaction_id": transaction_id,
            "message": "Order created successfully"
        }
        
    except Exception as e:
        logging.error(f"Order creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")

@api_router.post("/verify-payment")
async def verify_razorpay_payment(
    order_id: str,
    payment_id: str, 
    signature: str,
    current_user: User = Depends(get_current_user)
):
    """Verify Razorpay payment and update status"""
    try:
        # Verify signature
        if not verify_razorpay_signature(order_id, payment_id, signature):
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        # Get payment details from Razorpay
        payment_details = razorpay_client.payment.fetch(payment_id)
        
        # Update payment record
        await db.payments.update_one(
            {"phonepe_order_id": order_id},
            {
                "$set": {
                    "status": "SUCCESS",
                    "updated_at": datetime.utcnow(),
                    "razorpay_payment_id": payment_id,
                    "payment_method": payment_details.get("method"),
                }
            }
        )
        
        # If it's a subscription payment, activate subscription
        payment_record = await db.payments.find_one({"phonepe_order_id": order_id})
        if payment_record and payment_record["payment_type"] == "subscription":
            await activate_subscription(payment_record["student_id"], payment_record["description"])
        
        return {
            "success": True,
            "message": "Payment verified successfully",
            "payment_id": payment_id,
            "status": "SUCCESS"
        }
        
    except Exception as e:
        logging.error(f"Payment verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")

@api_router.post("/create-subscription")
async def create_subscription(
    subscription_request: SubscriptionRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a subscription order"""
    try:
        # Get subscription plan
        plans = await get_subscription_plans()
        plan = next((p for p in plans["plans"] if p["id"] == subscription_request.plan_id), None)
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        
        # Generate subscription ID
        subscription_id = f"SUB_{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        # Create Razorpay order for first month payment
        order_data = {
            "amount": plan["monthly_amount"],
            "currency": "INR", 
            "receipt": subscription_id,
            "notes": {
                "student_id": current_user.id,
                "plan_id": subscription_request.plan_id,
                "subscription_type": "monthly_premium",
                "plan_name": plan["name"]
            }
        }
        
        razorpay_order = razorpay_client.order.create(order_data)
        
        # Store subscription record
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30 * subscription_request.duration_months)
        
        subscription = Subscription(
            id=subscription_id,
            student_id=current_user.id,
            plan_id=subscription_request.plan_id,
            status="PENDING",
            start_date=start_date,
            end_date=end_date,
            monthly_amount=plan["monthly_amount"]
        )
        
        await db.subscriptions.insert_one(subscription.dict())
        
        # Create payment record for subscription
        payment_record = PaymentRecord(
            transaction_id=subscription_id,
            student_id=current_user.id,
            amount=plan["monthly_amount"],
            payment_type="subscription",
            status="CREATED",
            description=f"Subscription to {plan['name']}",
            phonepe_order_id=razorpay_order["id"]
        )
        
        await db.payments.insert_one(payment_record.dict())
        
        return {
            "success": True,
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": RAZORPAY_KEY_ID,
            "subscription_id": subscription_id,
            "message": "Subscription order created successfully"
        }
        
    except Exception as e:
        logging.error(f"Subscription creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Subscription creation failed: {str(e)}")

async def activate_subscription(student_id: str, plan_description: str):
    """Activate subscription after successful payment"""
    try:
        await db.subscriptions.update_one(
            {"student_id": student_id, "status": "PENDING"},
            {
                "$set": {
                    "status": "ACTIVE",
                    "last_payment_date": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logging.info(f"Subscription activated for student: {student_id}")
    except Exception as e:
        logging.error(f"Failed to activate subscription: {e}")

@api_router.get("/payment-status/{transaction_id}")
async def get_payment_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get payment status"""
    try:
        # Get payment record from database
        payment_record = await db.payments.find_one({"transaction_id": transaction_id})
        if not payment_record:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Get order details from Razorpay if needed
        razorpay_status = "UNKNOWN"
        if payment_record.get("phonepe_order_id"):
            try:
                order_details = razorpay_client.order.fetch(payment_record["phonepe_order_id"])
                razorpay_status = order_details["status"]
            except Exception as e:
                logging.warning(f"Failed to fetch Razorpay order status: {e}")
        
        return {
            "transaction_id": transaction_id,
            "status": payment_record["status"],
            "amount": payment_record["amount"],
            "created_at": payment_record["created_at"],
            "razorpay_order_id": payment_record.get("phonepe_order_id"),
            "razorpay_status": razorpay_status
        }
        
    except Exception as e:
        logging.error(f"Payment status check error: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@api_router.post("/razorpay-webhook")
async def handle_razorpay_webhook(request: Request):
    """Handle Razorpay webhook notifications"""
    try:
        # Get webhook body and signature
        body = await request.body()
        signature = request.headers.get("x-razorpay-signature")
        
        if not signature:
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Verify webhook signature
        try:
            razorpay_client.utility.verify_webhook_signature(
                body.decode("utf-8"), signature, RAZORPAY_WEBHOOK_SECRET
            )
        except razorpay.errors.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        # Parse webhook data
        webhook_data = json.loads(body.decode("utf-8"))
        event = webhook_data["event"]
        payload = webhook_data["payload"]
        
        # Handle different webhook events
        if event == "payment.captured":
            await handle_payment_success(payload["payment"]["entity"])
        elif event == "payment.failed":
            await handle_payment_failure(payload["payment"]["entity"])
        elif event == "order.paid":
            await handle_order_completion(payload["order"]["entity"])
        
        return {"status": "success", "message": "Webhook processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

async def handle_payment_success(payment_entity: dict):
    """Handle successful payment webhook"""
    try:
        order_id = payment_entity["order_id"]
        payment_id = payment_entity["id"]
        amount = payment_entity["amount"]
        
        # Update payment record
        await db.payments.update_one(
            {"phonepe_order_id": order_id},
            {
                "$set": {
                    "status": "SUCCESS",
                    "updated_at": datetime.utcnow(),
                    "razorpay_payment_id": payment_id,
                    "payment_method": payment_entity.get("method"),
                }
            }
        )
        
        # Handle subscription activation
        payment_record = await db.payments.find_one({"phonepe_order_id": order_id})
        if payment_record and payment_record["payment_type"] == "subscription":
            await activate_subscription(payment_record["student_id"], payment_record["description"])
        
        logging.info(f"Payment success processed for order: {order_id}")
        
    except Exception as e:
        logging.error(f"Error processing payment success: {e}")

async def handle_payment_failure(payment_entity: dict):
    """Handle failed payment webhook"""
    try:
        order_id = payment_entity["order_id"]
        
        # Update payment record
        await db.payments.update_one(
            {"phonepe_order_id": order_id},
            {
                "$set": {
                    "status": "FAILED",
                    "updated_at": datetime.utcnow(),
                    "failure_reason": payment_entity.get("error_description")
                }
            }
        )
        
        logging.info(f"Payment failure processed for order: {order_id}")
        
    except Exception as e:
        logging.error(f"Error processing payment failure: {e}")

async def handle_order_completion(order_entity: dict):
    """Handle order completion webhook"""
    try:
        order_id = order_entity["id"]
        
        logging.info(f"Order completed: {order_id}")
        
    except Exception as e:
        logging.error(f"Error processing order completion: {e}")

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

async def create_rag_embeddings(material_id: str, pages_text: List[str]):
    """Create embeddings for RAG system"""
    try:
        collection_name = f"material_{material_id}"
        
        try:
            collection = chroma_client.get_collection(collection_name)
        except:
            collection = chroma_client.create_collection(collection_name)
        
        # Create embeddings for each page
        for page_num, text in enumerate(pages_text):
            if text.strip():  # Only process non-empty pages
                # Generate embedding
                embedding = sentence_model.encode(text)
                
                # Add to vector database
                collection.add(
                    embeddings=[embedding.tolist()],
                    documents=[text],
                    metadatas=[{"page_number": page_num, "material_id": material_id}],
                    ids=[f"{material_id}_page_{page_num}"]
                )
                
                # Store document record
                rag_doc = RAGDocument(
                    material_id=material_id,
                    content=text,
                    page_number=page_num,
                    embedding_id=f"{material_id}_page_{page_num}"
                )
                await db.rag_documents.insert_one(rag_doc.dict())
        
        return True
    except Exception as e:
        logging.error(f"RAG embedding error: {e}")
        return False

async def query_rag_system(question: str, subject: str = None, grade_level: str = None) -> str:
    """Query RAG system for course-related answers"""
    try:
        # Get all relevant collections
        collections = chroma_client.list_collections()
        
        if not collections:
            return "No study materials have been uploaded yet. Please ask your teacher to upload course materials."
        
        # Generate query embedding
        query_embedding = sentence_model.encode(question)
        
        # Search across all material collections
        all_results = []
        for collection in collections:
            try:
                results = collection.query(
                    query_embeddings=[query_embedding.tolist()],
                    n_results=3
                )
                if results['documents']:
                    all_results.extend(results['documents'][0])
            except:
                continue
        
        if not all_results:
            return "I couldn't find relevant information in the uploaded materials. Please try a different question."
        
        # Use Gemini to generate answer based on retrieved context
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        context = "\n\n".join(all_results[:3])  # Use top 3 results
        
        prompt = f"""Based on the following course materials, answer the student's question:

Course Materials Context:
{context}

Student Question: {question}

Please provide a clear, educational answer based on the course materials. If the materials don't contain enough information, mention that and provide what you can. Make the answer appropriate for {grade_level or 'general'} level in {subject or 'the subject'}."""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logging.error(f"RAG query error: {e}")
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

@api_router.get("/my-subscription")
async def get_my_subscription(current_user: User = Depends(get_current_user)):
    """Get current user's subscription"""
    try:
        subscription = await db.subscriptions.find_one(
            {"student_id": current_user.id, "status": {"$in": ["ACTIVE", "PENDING"]}}
        )
        
        if not subscription:
            return {"has_subscription": False, "message": "No active subscription"}
        
        # Remove ObjectId to avoid serialization issues
        clean_subscription = {k: v for k, v in subscription.items() if k != "_id"}
        
        return {
            "has_subscription": True,
            "subscription": clean_subscription,
            "expires_at": subscription["end_date"],
            "is_active": subscription["status"] == "ACTIVE"
        }
        
    except Exception as e:
        logging.error(f"Subscription check error: {e}")
        return {"has_subscription": False, "error": str(e)}

@api_router.get("/payment-success")
async def payment_success_page(transaction_id: str = None):
    """Payment success redirect page"""
    return {
        "message": "Payment completed successfully!",
        "transaction_id": transaction_id,
        "redirect_to": f"{CALLBACK_BASE_URL}?payment=success"
    }

@api_router.get("/payment-failure") 
async def payment_failure_page(transaction_id: str = None):
    """Payment failure redirect page"""
    return {
        "message": "Payment failed. Please try again.",
        "transaction_id": transaction_id,
        "redirect_to": f"{CALLBACK_BASE_URL}?payment=failed"
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
            success = await create_rag_embeddings(study_material.id, pages_text)
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
    try:
        if current_user.role != "teacher":
            raise HTTPException(status_code=403, detail="Teacher access required")
        
        materials = await db.study_materials.find({"uploaded_by": current_user.id}).to_list(100)
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
    """Ask questions based on uploaded course materials"""
    try:
        answer = await query_rag_system(
            query_request.question,
            query_request.subject,
            query_request.grade_level
        )
        
        # Save question for tracking
        question_record = Question(
            student_id=current_user.id,
            question=query_request.question,
            subject=query_request.subject or "General",
            answer=answer,
            answered_by="RAG_AI"
        )
        
        await db.questions.insert_one(question_record.dict())
        
        return {
            "question": query_request.question,
            "answer": answer,
            "source": "course_materials",
            "answered_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"RAG question error: {e}")
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

class NoteCreateRequest(BaseModel):
    title: str
    content: str
    subject: str
    tags: List[str] = []

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
        
        return {"success": True, "note_id": note.id, "message": "Note created successfully"}
        
    except Exception as e:
        logging.error(f"Note creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/notes/my-notes")
async def get_my_notes(current_user: User = Depends(get_current_user)):
    """Get all notes for current user"""
    try:
        notes = await db.student_notes.find({"student_id": current_user.id}).sort("updated_at", -1).to_list(100)
        return {"notes": notes}
        
    except Exception as e:
        logging.error(f"Get notes error: {e}")
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

@api_router.get("/parent/progress-report/{student_id}")
async def get_student_progress_report(
    student_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive progress report for parents"""
    try:
        # Verify parent access (in real app, you'd have proper parent-child linking)
        if current_user.role != "parent":
            raise HTTPException(status_code=403, detail="Parent access required")
        
        # Generate progress report
        report = await generate_progress_report(student_id, current_user.id)
        
        return report
        
    except Exception as e:
        logging.error(f"Progress report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/parent/students")
async def get_linked_students(current_user: User = Depends(get_current_user)):
    """Get students linked to parent account"""
    try:
        if current_user.role != "parent":
            raise HTTPException(status_code=403, detail="Parent access required")
        
        # For demo purposes, return all students
        # In real app, you'd have proper parent-child relationships
        students_docs = await db.users.find({"role": "student"}).to_list(100)
        
        # Convert to User objects to avoid ObjectId serialization issues
        students = []
        for doc in students_docs:
            # Remove MongoDB ObjectId and password fields
            clean_doc = {k: v for k, v in doc.items() if k not in ["_id", "password"]}
            students.append(clean_doc)
        
        return {"students": students}
        
    except Exception as e:
        logging.error(f"Linked students error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= GENERAL ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "EduAgent API - AI Powered Educational Platform with Payment Gateway"}

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
