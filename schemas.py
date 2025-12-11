from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime


# -------------------- Auth & Users --------------------

class UserCreate(BaseModel):
    full_name: Optional[str] = None
    email: EmailStr
    password: str
    role: Literal["teacher", "student"]  # ✅ FIXED (no regex)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    full_name: Optional[str]
    email: EmailStr
    role: str
    created_at: Optional[datetime]

    class Config:
        orm_mode = True


# -------------------- Classes --------------------

class CreateClass(BaseModel):
    class_name: str


class JoinClass(BaseModel):
    join_code: str


# -------------------- Polls --------------------

class PollOptionIn(BaseModel):
    option_text: str


class PollCreate(BaseModel):
    class_id: int
    question: str
    options: List[PollOptionIn]


class PollVote(BaseModel):
    option_id: int


# -------------------- Quizzes --------------------

class QuizOptionIn(BaseModel):
    option_text: str


class QuizQuestionIn(BaseModel):
    question_text: str
    options: List[QuizOptionIn]
    correct_option_index: int


class QuizCreate(BaseModel):
    class_id: int
    title: str
    timer: Optional[int] = None
    questions: List[QuizQuestionIn]


class QuizAnswer(BaseModel):
    question_id: int
    option_id: int


class QuizSubmitPayload(BaseModel):
    answers: List[QuizAnswer]
