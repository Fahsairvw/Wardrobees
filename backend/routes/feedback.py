from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import get_user, save_feedback, get_all_feedback

router = APIRouter(prefix='/feedback', tags=['Feedback'])


class FeedbackCreate(BaseModel):
    user_id: int
    comment: str


@router.post('')
def submit_feedback(body: FeedbackCreate):
    """Submit feedback from user."""
    if not get_user(body.user_id):
        raise HTTPException(404, 'User not found')
    return save_feedback(body.user_id, body.comment)


@router.get('')
def list_feedback(approved_only: bool = False):
    """List all feedback (admin access)."""
    return get_all_feedback(approved_only)
