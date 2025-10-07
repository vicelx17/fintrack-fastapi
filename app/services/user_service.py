from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import hash_password
from app.models.category import Category
from app.models.user import User
from app.schemas.user import UserUpdate

DEFAULT_CATEGORIES = [
    "Alimentación",
    "Ocio",
    "Trabajo",
    "Suscripciones",
    "Viajes",
    "Transporte",
    "Facturas",
    "Otros"
]

async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def register_user(db: AsyncSession, first_name: str, last_name: str, username: str, email: str, password: str,
                        role: str) -> User:
    result = await db.execute(select(User).filter(User.username == username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )

    try:
        hashed_pwd = hash_password(password)
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            hashed_password=hashed_pwd,
            role=role
        )
        db.add(new_user)

        # Flush para obtener el ID del usuario sin hacer commit
        await db.flush()

        print(f"Usuario creado con ID: {new_user.id}")

        # Crear categorías por defecto en la misma transacción
        for category_name in DEFAULT_CATEGORIES:
            new_category = Category(
                user_id=new_user.id,
                name=category_name
            )
            db.add(new_category)
            print(f"Añadiendo categoría: {category_name} para usuario {new_user.id}")

        # Commit único para usuario y categorías
        await db.commit()
        await db.refresh(new_user)

        print(f"Usuario y categorías guardados exitosamente")

        return new_user

    except Exception as e:
        await db.rollback()
        print(f"Error al registrar usuario: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

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
