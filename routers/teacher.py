from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import string
import random

from database import get_db
from deps import require_teacher
from models import (
    Class,
    User,
    Poll,
    PollOption,
    PollResponse,
    Quiz,
    QuizQuestion,
    QuizOption,
    QuizResponse,
)
from schemas import CreateClass, PollCreate, QuizCreate

router = APIRouter(prefix="/teacher", tags=["Teacher"])


def generate_join_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# --------------------------------------------------
#                     CLASSES
# --------------------------------------------------

@router.post("/classes")
def create_class(
    payload: CreateClass,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    code = generate_join_code()
    while db.query(Class).filter(Class.join_code == code).first():
        code = generate_join_code()

    new_class = Class(
        teacher_id=teacher.id,
        class_name=payload.class_name,
        join_code=code,
    )

    db.add(new_class)
    db.commit()
    db.refresh(new_class)

    return {
        "status": "success",
        "message": "Class created",
        "data": {"id": new_class.id, "join_code": new_class.join_code},
    }


@router.get("/classes")
def list_classes(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    classes = db.query(Class).filter(Class.teacher_id == teacher.id).all()
    return {
        "status": "success",
        "data": [
            {"id": c.id, "class_name": c.class_name, "join_code": c.join_code}
            for c in classes
        ],
    }


# --------------------------------------------------
#                     POLLS
# --------------------------------------------------

@router.post("/polls")
def create_poll(
    payload: PollCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    cls = (
        db.query(Class)
        .filter(Class.id == payload.class_id, Class.teacher_id == teacher.id)
        .first()
    )

    if not cls:
        raise HTTPException(
            status_code=404,
            detail="Class not found or not owned by you",
        )

    poll = Poll(class_id=payload.class_id, question=payload.question, status="draft")
    db.add(poll)
    db.flush()

    for opt in payload.options:
        db.add(PollOption(poll_id=poll.id, option_text=opt.option_text))

    db.commit()
    db.refresh(poll)

    return {"status": "success", "data": {"poll_id": poll.id}}


@router.get("/polls")
def list_polls(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    polls = (
        db.query(
            Poll,
            func.count(PollOption.id).label("option_count"),
        )
        .join(Class, Poll.class_id == Class.id)
        .outerjoin(PollOption, PollOption.poll_id == Poll.id)
        .filter(Class.teacher_id == teacher.id)
        .group_by(Poll.id)
        .all()
    )

    return {
        "status": "success",
        "data": [
            {
                "id": p.Poll.id,
                "question": p.Poll.question,
                "class_id": p.Poll.class_id,
                "status": p.Poll.status,
                "option_count": p.option_count,
            }
            for p in polls
        ],
    }


@router.patch("/polls/{poll_id}/status")
def set_poll_status(
    poll_id: int,
    new_status: str,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    poll = (
        db.query(Poll)
        .join(Class)
        .filter(Poll.id == poll_id, Class.teacher_id == teacher.id)
        .first()
    )

    if not poll:
        raise HTTPException(404, "Poll not found")

    if new_status not in ("draft", "live", "closed"):
        raise HTTPException(400, "Invalid status")

    poll.status = new_status
    db.commit()
    return {"status": "success", "message": f"Poll status set to {new_status}"}


@router.get("/polls/{poll_id}/results")
def poll_results(
    poll_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    poll = (
        db.query(Poll)
        .join(Class)
        .filter(Poll.id == poll_id, Class.teacher_id == teacher.id)
        .first()
    )

    if not poll:
        raise HTTPException(404, "Poll not found")

    options = db.query(PollOption).filter(PollOption.poll_id == poll_id).all()
    total_votes = db.query(PollResponse).filter(PollResponse.poll_id == poll_id).count()

    results = []
    for option in options:
        votes = db.query(PollResponse).filter(PollResponse.option_id == option.id).count()
        percentage = (votes / total_votes * 100) if total_votes else 0
        results.append(
            {
                "option_id": option.id,
                "option_text": option.option_text,
                "votes": votes,
                "percentage": percentage,
            }
        )

    return {"status": "success", "data": {"total_votes": total_votes, "results": results}}


# --------------------------------------------------
#                     QUIZZES
# --------------------------------------------------

@router.post("/quizzes")
def create_quiz(
    payload: QuizCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    cls = (
        db.query(Class)
        .filter(Class.id == payload.class_id, Class.teacher_id == teacher.id)
        .first()
    )

    if not cls:
        raise HTTPException(404, "Class not found or not owned by you")

    quiz = Quiz(
        class_id=payload.class_id,
        title=payload.title,
        timer=payload.timer,
        status="draft",
    )
    db.add(quiz)
    db.flush()

    for q in payload.questions:
        question = QuizQuestion(quiz_id=quiz.id, question_text=q.question_text)
        db.add(question)
        db.flush()

        option_ids = []
        for opt in q.options:
            option = QuizOption(question_id=question.id, option_text=opt.option_text)
            db.add(option)
            db.flush()
            option_ids.append(option.id)

        if 0 <= q.correct_option_index < len(option_ids):
            question.correct_option_id = option_ids[q.correct_option_index]
            db.add(question)

    db.commit()
    db.refresh(quiz)

    return {"status": "success", "data": {"quiz_id": quiz.id}}


@router.get("/quizzes")
def list_quizzes(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    quizzes = (
        db.query(
            Quiz,
            func.count(QuizQuestion.id).label("question_count"),
        )
        .join(Class, Quiz.class_id == Class.id)
        .outerjoin(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
        .filter(Class.teacher_id == teacher.id)
        .group_by(Quiz.id)
        .all()
    )

    return {
        "status": "success",
        "data": [
            {
                "id": q.Quiz.id,
                "title": q.Quiz.title,
                "class_id": q.Quiz.class_id,
                "status": q.Quiz.status,
                "timer": q.Quiz.timer,
                "question_count": q.question_count,
            }
            for q in quizzes
        ],
    }


@router.patch("/quizzes/{quiz_id}/status")
def set_quiz_status(
    quiz_id: int,
    new_status: str,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .join(Class)
        .filter(Quiz.id == quiz_id, Class.teacher_id == teacher.id)
        .first()
    )

    if not quiz:
        raise HTTPException(404, "Quiz not found")

    if new_status not in ("draft", "live", "closed"):
        raise HTTPException(400, "Invalid status")

    quiz.status = new_status
    db.commit()
    return {"status": "success", "message": f"Quiz status set to {new_status}"}


@router.get("/quizzes/{quiz_id}/results")
def quiz_results(
    quiz_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .join(Class)
        .filter(Quiz.id == quiz_id, Class.teacher_id == teacher.id)
        .first()
    )

    if not quiz:
        raise HTTPException(404, "Quiz not found")

    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()

    student_ids = [
        s[0]
        for s in db.query(QuizResponse.student_id)
        .filter(QuizResponse.quiz_id == quiz_id)
        .distinct()
        .all()
    ]

    results = []

    for sid in student_ids:
        correct = 0
        total = len(questions)
        details = []

        for question in questions:
            response = (
                db.query(QuizResponse)
                .filter(
                    QuizResponse.quiz_id == quiz_id,
                    QuizResponse.question_id == question.id,
                    QuizResponse.student_id == sid,
                )
                .first()
            )

            is_correct = (
                response is not None
                and question.correct_option_id is not None
                and response.option_id == question.correct_option_id
            )

            if is_correct:
                correct += 1

            details.append({"question_id": question.id, "correct": is_correct})

        percentage = (correct / total * 100) if total else 0

        results.append(
            {
                "student_id": sid,
                "score": correct,
                "total": total,
                "percentage": percentage,
                "details": details,
            }
        )

    return {"status": "success", "data": results}
