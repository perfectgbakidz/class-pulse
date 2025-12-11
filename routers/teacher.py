from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
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


# -------------------- Classes --------------------

@router.post("/classes")
def create_class(
    payload: CreateClass,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    code = generate_join_code()
    while db.query(Class).filter(Class.join_code == code).first() is not None:
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


# -------------------- Polls --------------------

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

    if cls is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found or not owned by you",
        )

    poll = Poll(class_id=payload.class_id, question=payload.question, status="draft")
    db.add(poll)
    db.flush()  # ensure poll.id exists

    for opt in payload.options:
        option = PollOption(poll_id=poll.id, option_text=opt.option_text)
        db.add(option)
        db.flush()  # ensure option is saved

    db.commit()
    db.refresh(poll)

    return {"status": "success", "data": {"poll_id": poll.id}}


@router.get("/polls")
def list_polls(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    polls = db.query(Poll).join(Class).filter(Class.teacher_id == teacher.id).all()
    return {
        "status": "success",
        "data": [
            {"id": p.id, "question": p.question, "class_id": p.class_id, "status": p.status}
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

    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    if new_status not in ("draft", "live", "closed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

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

    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    options = db.query(PollOption).filter(PollOption.poll_id == poll_id).all()
    total_votes = db.query(PollResponse).filter(PollResponse.poll_id == poll_id).count()

    results = []
    for option in options:
        votes = db.query(PollResponse).filter(PollResponse.option_id == option.id).count()
        percentage = (votes / total_votes * 100) if total_votes > 0 else 0.0
        results.append(
            {"option_id": option.id, "option_text": option.option_text, "votes": votes, "percentage": percentage}
        )

    return {"status": "success", "data": {"total_votes": total_votes, "results": results}}


# -------------------- Quizzes --------------------

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

    if cls is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found or not owned by you",
        )

    quiz = Quiz(class_id=payload.class_id, title=payload.title, timer=payload.timer, status="draft")
    db.add(quiz)
    db.flush()   # make sure quiz.id exists

    for q in payload.questions:
        question = QuizQuestion(quiz_id=quiz.id, question_text=q.question_text)
        db.add(question)
        db.flush()  # ensure question.id exists

        option_ids = []
        for opt in q.options:
            option = QuizOption(question_id=question.id, option_text=opt.option_text)
            db.add(option)
            db.flush()  # ensure option.id exists
            option_ids.append(option.id)

        # Save correct answer
        if 0 <= q.correct_option_index < len(option_ids):
            question.correct_option_id = option_ids[q.correct_option_index]
            db.add(question)

        db.flush()

    db.commit()
    db.refresh(quiz)

    return {"status": "success", "data": {"quiz_id": quiz.id}}


@router.get("/quizzes")
def list_quizzes(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    quizzes = db.query(Quiz).join(Class).filter(Class.teacher_id == teacher.id).all()
    return {
        "status": "success",
        "data": [
            {"id": q.id, "title": q.title, "class_id": q.class_id, "status": q.status, "timer": q.timer}
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

    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    if new_status not in ("draft", "live", "closed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

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

    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
    student_ids = [
        sid[0]
        for sid in db.query(QuizResponse.student_id)
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

        percentage = (correct / total * 100) if total > 0 else 0.0

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
