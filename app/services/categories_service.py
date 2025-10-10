from sqlalchemy import update, delete, and_
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
    from sqlalchemy import func
    from app.models.transaction import Transaction

    result = await db.execute(
        select(
            Category,
            func.count(Transaction.id).label('transaction_count')
        )
        .outerjoin(Transaction, and_(
            Category.id == Transaction.category_id,
            Transaction.user_id == user_id
        ))
        .where(Category.user_id == user_id)
        .group_by(Category.id)
    )

    categories_with_count = []
    for row in result:
        category = row[0]
        count = row[1]
        categories_with_count.append({
            "id": category.id,
            "name": category.name,
            "user_id": category.user_id,
            "transaction_count": count or 0
        })

    return categories_with_count


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
