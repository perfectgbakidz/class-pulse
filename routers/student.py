from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from deps import require_student
from models import Quiz, QuizQuestion, QuizResponse, ClassMember, Class, User
from schemas import QuizSubmitPayload, JoinClass

router = APIRouter(prefix="/student", tags=["Student"])


# -----------------------------------------------------------
#                     Get My Classes
# -----------------------------------------------------------
@router.get("/classes")
def get_my_classes(student: User = Depends(require_student), db: Session = Depends(get_db)):
    if not student or not getattr(student, "id", None):
        raise HTTPException(status_code=400, detail="Invalid student credentials")

    memberships = db.query(ClassMember).filter(ClassMember.student_id == student.id).all()
    class_list = []

    for m in memberships:
        cls = db.query(Class).filter(Class.id == m.class_id).first()
        if cls:
            class_list.append({
                "class_id": cls.id,
                "class_name": cls.class_name,
                "teacher_id": cls.teacher_id,
                "teacher_name": cls.teacher.full_name if cls.teacher else None,
                "join_code": cls.join_code
            })

    return {"status": "success", "data": class_list}


# -----------------------------------------------------------
#                     List My Quizzes
# -----------------------------------------------------------
@router.get("/quizzes")
def get_my_quizzes(student: User = Depends(require_student), db: Session = Depends(get_db)):

    memberships = db.query(ClassMember).filter(ClassMember.student_id == student.id).all()
    class_ids = [m.class_id for m in memberships]

    # Include question count
    quizzes = (
        db.query(
            Quiz.id.label("quiz_id"),
            Quiz.class_id,
            Quiz.title,
            Quiz.timer,
            Quiz.status,
            Quiz.created_at,
            func.count(QuizQuestion.id).label("question_count")
        )
        .outerjoin(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
        .filter(Quiz.class_id.in_(class_ids))
        .group_by(Quiz.id)
        .all()
    )

    quiz_list = [
        {
            "quiz_id": q.quiz_id,
            "class_id": q.class_id,
            "title": q.title,
            "timer": q.timer,
            "status": q.status,
            "created_at": q.created_at,
            "question_count": q.question_count
        }
        for q in quizzes
    ]

    return {"status": "success", "data": quiz_list}


# -----------------------------------------------------------
#                       Join Class
# -----------------------------------------------------------
@router.post("/classes/join")
def join_class(
    payload: JoinClass,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    cls = db.query(Class).filter(Class.join_code == payload.join_code).first()
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    membership = db.query(ClassMember).filter(
        ClassMember.class_id == cls.id,
        ClassMember.student_id == student.id,
    ).first()

    if membership:
        raise HTTPException(status_code=409, detail="Already a member of this class")

    new_member = ClassMember(class_id=cls.id, student_id=student.id)
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return {
        "status": "success",
        "message": f"Joined class '{cls.class_name}' successfully",
        "data": {"class_id": cls.id, "class_name": cls.class_name},
    }


# -----------------------------------------------------------
#                    Submit Quiz
# -----------------------------------------------------------
@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitPayload,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not available")

    membership = db.query(ClassMember).filter(
        ClassMember.class_id == quiz.class_id,
        ClassMember.student_id == student.id,
    ).first()
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this class")

    existing = db.query(QuizResponse).filter(
        QuizResponse.quiz_id == quiz_id,
        QuizResponse.student_id == student.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Quiz already submitted")

    # Save responses
    for ans in payload.answers:
        response = QuizResponse(
            quiz_id=quiz_id,
            question_id=ans.question_id,
            student_id=student.id,
            option_id=ans.option_id
        )
        db.add(response)

    db.commit()

    # Calculate results
    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
    correct = 0
    details = []

    for question in questions:
        response = db.query(QuizResponse).filter(
            QuizResponse.quiz_id == quiz_id,
            QuizResponse.question_id == question.id,
            QuizResponse.student_id == student.id
        ).first()

        is_correct = response is not None and response.option_id == question.correct_option_id
        if is_correct:
            correct += 1

        details.append({"question_id": question.id, "correct": is_correct})

    total = len(questions)
    percentage = (correct / total * 100) if total > 0 else 0

    return {
        "status": "success",
        "data": {
            "score": correct,
            "total": total,
            "percentage": percentage,
            "details": details
        },
    }


# -----------------------------------------------------------
#                   Quiz Result (My Result)
# -----------------------------------------------------------
@router.get("/quizzes/{quiz_id}/results")
def my_quiz_result(
    quiz_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    membership = db.query(ClassMember).filter(
        ClassMember.class_id == quiz.class_id,
        ClassMember.student_id == student.id,
    ).first()
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this class")

    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
    correct = 0
    details = []

    for question in questions:
        response = db.query(QuizResponse).filter(
            QuizResponse.quiz_id == quiz_id,
            QuizResponse.question_id == question.id,
            QuizResponse.student_id == student.id
        ).first()

        is_correct = response is not None and response.option_id == question.correct_option_id

        if is_correct:
            correct += 1

        details.append({"question_id": question.id, "correct": is_correct})

    total = len(questions)
    percentage = (correct / total * 100) if total > 0 else 0

    return {
        "status": "success",
        "data": {
            "score": correct,
            "total": total,
            "percentage": percentage,
            "details": details
        },
    }
