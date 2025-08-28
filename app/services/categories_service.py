from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.category import Category
from app.schemas.category import CategoryUpdate, CategoryCreate


async def create_category(db: AsyncSession, user_id: int, category: CategoryCreate):
    new_category = Category(
        user_id=user_id,
        name=category.name,
    )
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category

async def get_categories(db: AsyncSession, user_id: int):
    result = await db.execute(select(Category).where(Category.user_id == user_id))
    return result.scalars().all()

async def get_category_by_id(db: AsyncSession, user_id: int, category_id: int):
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    return result.scalars().one_or_none()

async def update_category(db: AsyncSession, user_id: int, category_id: int, category_update: CategoryUpdate):
    query = (
        update(Category)
        .where(Category.id == category_id, Category.user_id == user_id)
        .values(category_update.model_dump(exclude_unset=True))
        .returning(Category)
    )
    result = await db.execute(query)
    await db.commit()
    return result.scalars().one_or_none()

async def delete_category(db: AsyncSession, user_id: int, category_id: int):
    query = delete(Category).where(Category.id == category_id, Category.user_id == user_id)
    await db.execute(query)
    await db.commit()
    return {"message": "Category deleted"}