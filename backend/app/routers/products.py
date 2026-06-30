"""
Product endpoints.
GET /api/products/search?q=...&category=...&customer_id=...
GET /api/products/{id}?customer_id=...
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product, Customer
from app.schemas import ProductOut, ProductSearchResult
from app.currency import convert_price

router = APIRouter(tags=["products"])


def _apply_currency(products_data: list[dict], customer_currency: str) -> list[dict]:
    """Apply currency conversion to a list of product dicts."""
    result = []
    for p in products_data:
        converted_price, cur, sym = convert_price(p["price"], customer_currency)
        p["price"] = converted_price
        p["currency"] = cur
        p["symbol"] = sym
        result.append(p)
    return result


@router.get("/products/categories", response_model=list[str])
async def get_product_categories(
    db: AsyncSession = Depends(get_db),
):
    """Get all unique product categories."""
    result = await db.execute(select(Product.category).distinct().order_by(Product.category))
    categories = result.scalars().all()
    return [c for c in categories if c]


@router.get("/products/search", response_model=list[ProductSearchResult])
async def search_products(
    q: str = Query(default="", description="Search query for product name or brand"),
    category: str = Query(default="", description="Filter by product category"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    customer_id: str = Query(default="", description="Optional customer ID for currency conversion"),
    db: AsyncSession = Depends(get_db),
):
    """Search products by name, brand, or category with optional category filter."""
    stmt = select(Product)

    filters = []
    if q.strip():
        pattern = f"%{q.lower()}%"
        filters.append(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.brand).like(pattern),
                func.lower(Product.category).like(pattern),
            )
        )

    if category.strip():
        filters.append(func.lower(Product.category) == category.strip().lower())

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Product.name).limit(limit)

    result = await db.execute(stmt)
    products = result.scalars().all()

    # Determine customer currency for conversion
    customer_currency = "USD"
    if customer_id:
        cust_result = await db.execute(
            select(Customer.currency).where(Customer.customer_id == customer_id)
        )
        cur = cust_result.scalar_one_or_none()
        if cur:
            customer_currency = cur

    out = []
    for p in products:
        converted_price, cur, sym = convert_price(p.price, customer_currency)
        out.append(ProductSearchResult(
            product_id=p.product_id,
            name=p.name,
            category=p.category or "",
            subcategory=p.subcategory or "",
            brand=p.brand or "",
            price=converted_price,
            currency=cur,
            symbol=sym,
            image_url=p.image_url or "",
        ))
    return out


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: str,
    customer_id: str = Query(default="", description="Optional customer ID for currency conversion"),
    db: AsyncSession = Depends(get_db),
):
    """Get full product details by ID."""
    result = await db.execute(
        select(Product).where(Product.product_id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Determine customer currency for conversion
    customer_currency = "USD"
    if customer_id:
        cust_result = await db.execute(
            select(Customer.currency).where(Customer.customer_id == customer_id)
        )
        cur = cust_result.scalar_one_or_none()
        if cur:
            customer_currency = cur

    converted_price, cur, sym = convert_price(product.price, customer_currency)

    return ProductOut(
        product_id=product.product_id,
        name=product.name,
        category=product.category or "",
        subcategory=product.subcategory or "",
        brand=product.brand or "",
        price=converted_price,
        currency=cur,
        symbol=sym,
        image_url=product.image_url or "",
    )
