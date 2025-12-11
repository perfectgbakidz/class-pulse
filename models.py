from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
)
from sqlalchemy.sql import func
from database import Base
from typing import Optional, List
import enum


# ---------------- ENUMS ---------------- #

class RoleEnum(str, enum.Enum):
    teacher = "teacher"
    student = "student"


# ---------------- USER ---------------- #

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    classes: Mapped[List["Class"]] = relationship(
        back_populates="teacher",
        cascade="all, delete"
    )


# ---------------- CLASS ---------------- #

class Class(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    class_name: Mapped[str] = mapped_column(String, nullable=False)
    join_code: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    teacher: Mapped["User"] = relationship(back_populates="classes")
    members: Mapped[List["ClassMember"]] = relationship(
        back_populates="class_",
        cascade="all, delete"
    )
    polls: Mapped[List["Poll"]] = relationship(
        back_populates="class_",
        cascade="all, delete"
    )
    quizzes: Mapped[List["Quiz"]] = relationship(
        back_populates="class_",
        cascade="all, delete"
    )


# ---------------- CLASS MEMBER ---------------- #

class ClassMember(Base):
    __tablename__ = "class_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    class_: Mapped["Class"] = relationship(back_populates="members")


# ---------------- POLL ---------------- #

class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    class_: Mapped["Class"] = relationship(back_populates="polls")
    options: Mapped[List["PollOption"]] = relationship(
        back_populates="poll",
        cascade="all, delete"
    )
    responses: Mapped[List["PollResponse"]] = relationship(
        back_populates="poll",
        cascade="all, delete"
    )


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"))
    option_text: Mapped[str] = mapped_column(String, nullable=False)

    poll: Mapped["Poll"] = relationship(back_populates="options")


class PollResponse(Base):
    __tablename__ = "poll_responses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    option_id: Mapped[int] = mapped_column(ForeignKey("poll_options.id"))
    responded_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    poll: Mapped["Poll"] = relationship(back_populates="responses")


# ---------------- QUIZ ---------------- #

class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    timer: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    class_: Mapped["Class"] = relationship(back_populates="quizzes")
    questions: Mapped[List["QuizQuestion"]] = relationship(
        back_populates="quiz",
        cascade="all, delete"
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_option_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    quiz: Mapped["Quiz"] = relationship(back_populates="questions")
    options: Mapped[List["QuizOption"]] = relationship(
        back_populates="question",
        cascade="all, delete"
    )


class QuizOption(Base):
    __tablename__ = "quiz_options"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"))
    option_text: Mapped[str] = mapped_column(String, nullable=False)

    question: Mapped["QuizQuestion"] = relationship(back_populates="options")


class QuizResponse(Base):
    __tablename__ = "quiz_responses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    option_id: Mapped[int] = mapped_column(ForeignKey("quiz_options.id"))
    responded_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
