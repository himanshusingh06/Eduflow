from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
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
from emergentintegrations.llm.chat import LlmChat, UserMessage
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
    answers: Dict[int, int]  # question_index: selected_option
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
    """Generate personalized study content using AI"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"study_content_{uuid.uuid4()}",
            system_message=f"You are an expert educator creating study content for {grade_level} students in {subject}."
        ).with_model("gemini", "gemini-2.5-pro")
        
        user_message = UserMessage(
            text=f"Create comprehensive study content about '{topic}' for {grade_level} students studying {subject}. Include key concepts, examples, and learning objectives. Make it engaging and age-appropriate."
        )
        
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logging.error(f"AI content generation error: {e}")
        return f"Study content for {topic}: This is a comprehensive overview of {topic} in {subject}. [AI generation failed, please try again]"

async def generate_quiz(topic: str, subject: str, grade_level: str, num_questions: int = 10, difficulty: str = "medium") -> List[QuizQuestion]:
    """Generate quiz questions using AI"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"quiz_gen_{uuid.uuid4()}",
            system_message=f"You are an expert quiz creator for {grade_level} students in {subject}."
        ).with_model("gemini", "gemini-2.5-pro")
        
        user_message = UserMessage(
            text=f"Generate {num_questions} multiple choice questions about '{topic}' for {grade_level} students in {subject}. Difficulty: {difficulty}. Format as JSON array with 'question', 'options' (array of 4 choices), 'correct_answer' (0-3 index), and 'explanation' fields."
        )
        
        response = await chat.send_message(user_message)
        
        # Parse AI response to extract JSON
        import re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
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
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"qa_{uuid.uuid4()}",
            system_message=f"You are a helpful tutor answering questions for students. Provide clear, educational answers appropriate for {grade_level} level in {subject}."
        ).with_model("gemini", "gemini-2.5-pro")
        
        user_message = UserMessage(
            text=f"Please answer this {subject} question clearly and educationally: {question}"
        )
        
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logging.error(f"AI answer generation error: {e}")
        return "I'm having trouble generating an answer right now. Please try again or consult your teacher."

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
    answers: Dict[int, int],
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
        if q_idx < len(quiz.questions):
            if quiz.questions[q_idx].correct_answer == selected_option:
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
    
    # Save attempt
    await db.quiz_attempts.insert_one(attempt.dict())
    
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

# ============= GENERAL ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "EduAgent API - AI Powered Educational Platform"}

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
