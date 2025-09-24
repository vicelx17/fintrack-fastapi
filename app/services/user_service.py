from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.models.user import User
from app.core.security import hash_password
from app.schemas.user import UserUpdate


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def register_user(db: AsyncSession,first_name:str, last_name:str, username: str, email: str, password: str, role: str) -> User:
    result = await db.execute(select(User).filter(User.username == username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate):
    updated_user = await get_user_by_id(db, user_id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user_data = user_update.model_dump(exclude_unset=True)


    if "password" in updated_user_data:
        password = updated_user_data.pop("password")
        updated_user_data["hashed_password"] = hash_password(password)

    for field, value in updated_user_data.items():
        setattr(updated_user, field, value)

    await db.commit()
    await db.refresh(updated_user)
    return updated_user

async def delete_user(db: AsyncSession, user_id: int):
    query = (delete(User).where(User.id == user_id))
    await db.execute(query)
    await db.commit()
    return {"message": "User deleted."}
