from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import create_user, get_user, get_or_create_wardrobe

router = APIRouter(prefix='/users', tags=['User'])


class UserCreate(BaseModel):
    name: str
    email: str
    user_role: str = 'user'


@router.post('')
def register_user(body: UserCreate):
    """
    Create or update a user.
    Auto-creates a wardrobe for new users.
    """
    user = create_user(body.name, body.email, body.user_role)
    wardrobe = get_or_create_wardrobe(user['user_id'])
    return {'user': user, 'wardrobe': wardrobe}


@router.get('/{user_id}')
def fetch_user(user_id: int):
    """Get user by ID."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, 'User not found')
    return user
