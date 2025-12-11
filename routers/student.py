from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import require_student
from models import Quiz, QuizQuestion, QuizResponse, ClassMember, User
from schemas import QuizSubmitPayload

router = APIRouter(prefix="/student", tags=["Student"])


@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitPayload,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    # ✅ Fetch quiz
    quiz: Quiz | None = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not available",
        )

    # ✅ Verify class membership
    membership = (
        db.query(ClassMember)
        .filter(
            ClassMember.class_id == quiz.class_id,
            ClassMember.student_id == student.id,
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this class",
        )

    # ✅ Prevent multiple submissions
    existing = (
        db.query(QuizResponse)
        .filter(
            QuizResponse.quiz_id == quiz_id,
            QuizResponse.student_id == student.id,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quiz already submitted",
        )

    # ✅ Save submitted answers
    for ans in payload.answers:
        response = QuizResponse(
            quiz_id=quiz_id,
            question_id=ans.question_id,
            student_id=student.id,
            option_id=ans.option_id,
        )
        db.add(response)

    db.commit()

    # ✅ Scoring logic
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .all()
    )

    correct = 0
    total = len(questions)
    details: list[dict] = []

    for question in questions:
        response = (
            db.query(QuizResponse)
            .filter(
                QuizResponse.quiz_id == quiz_id,
                QuizResponse.question_id == question.id,
                QuizResponse.student_id == student.id,
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

        details.append(
            {
                "question_id": question.id,
                "correct": is_correct,
            }
        )

    percentage = (correct / total * 100) if total > 0 else 0.0

    return {
        "status": "success",
        "data": {
            "score": correct,
            "total": total,
            "percentage": percentage,
            "details": details,
        },
    }


@router.get("/quizzes/{quiz_id}/results")
def my_quiz_result(
    quiz_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    # ✅ Fetch quiz
    quiz: Quiz | None = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    # ✅ Verify class membership
    membership = (
        db.query(ClassMember)
        .filter(
            ClassMember.class_id == quiz.class_id,
            ClassMember.student_id == student.id,
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this class",
        )

    # ✅ Scoring logic
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .all()
    )

    correct = 0
    total = len(questions)
    details: list[dict] = []

    for question in questions:
        response = (
            db.query(QuizResponse)
            .filter(
                QuizResponse.quiz_id == quiz_id,
                QuizResponse.question_id == question.id,
                QuizResponse.student_id == student.id,
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

        details.append(
            {
                "question_id": question.id,
                "correct": is_correct,
            }
        )

    percentage = (correct / total * 100) if total > 0 else 0.0

    return {
        "status": "success",
        "data": {
            "score": correct,
            "total": total,
            "percentage": percentage,
            "details": details,
        },
    }
