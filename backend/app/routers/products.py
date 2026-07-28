"""
Product endpoints.
GET /api/products/search?q=...&category=...&customer_id=...
GET /api/products/{id}?customer_id=...
"""
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product, Customer
from app.schemas import ProductOut, ProductSearchResult
from app.currency import convert_price

router = APIRouter(tags=["products"])



# Characters treated as separators — replaced with space for normalized matching
_SEPARATORS = '-_/\\.,:!@#$%^&*()+=[\\]{}|`~\'"'

# ── Synonym Map ──────────────────────────────────────────────────────────────
_SYNONYM_MAP: dict[str, list[str]] = {
    "mobile":           ["phone", "smartphone", "cellphone"],
    "smartphone":       ["mobile", "phone", "cellphone"],
    "phone":            ["mobile", "smartphone", "cellphone"],
    "cellphone":        ["mobile", "phone", "smartphone"],
    "laptop":           ["notebook", "notebook computer"],
    "notebook":         ["laptop"],
    "tv":               ["television"],
    "television":       ["tv"],
    "earphones":        ["earbuds", "headphones"],
    "earbuds":          ["earphones", "headphones"],
    "headphones":       ["earphones", "earbuds"],
    "tshirt":           ["t-shirt", "tee"],
    "t-shirt":          ["tshirt", "tee"],
    "tee":              ["tshirt", "t-shirt"],
    "sneakers":         ["shoes", "trainers"],
    "shoes":            ["sneakers", "trainers"],
    "trainers":         ["sneakers", "shoes"],
    "perfume":          ["fragrance", "scent"],
    "fragrance":        ["perfume", "scent"],
    "scent":            ["perfume", "fragrance"],
    "watch":            ["smartwatch"],
    "smartwatch":       ["watch"],
}


def _normalize_query(query: str) -> tuple[str, str]:
    lowered = query.lower().strip()
    spaced = re.sub(r'[' + re.escape(_SEPARATORS) + r']', ' ', lowered)
    spaced = re.sub(r'\s+', ' ', spaced).strip()
    compact = re.sub(r'[\s' + re.escape(_SEPARATORS) + r']', '', lowered)
    return spaced, compact


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
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    customer_id: str = Query(default="", description="Optional customer ID for currency conversion"),
    db: AsyncSession = Depends(get_db),
):
    """Search products by name, brand, or category with optional category filter."""
    stmt = select(Product)

    filters = []
    if q.strip():
        q_spaced, q_compact = _normalize_query(q)

        # Collect all search terms: the original query plus any synonym expansions
        search_terms = {q_spaced, q_compact}
        for word in q.lower().strip().split():
            for synonym in _SYNONYM_MAP.get(word, []):
                syn_spaced, syn_compact = _normalize_query(synonym)
                search_terms.add(syn_spaced)
                search_terms.add(syn_compact)

        # Build a LIKE condition for each search term against name, brand, category
        term_conditions = []
        for term in search_terms:
            like_pattern = f"%{term}%"
            term_conditions.append(
                or_(
                    func.lower(Product.name).like(like_pattern),
                    func.lower(Product.brand).like(like_pattern),
                    func.lower(Product.category).like(like_pattern),
                )
            )

        filters.append(or_(*term_conditions))

    if category.strip():
        filters.append(func.lower(Product.category) == category.strip().lower())

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Product.name)

    # Only apply limit when there's an actual search query or category filter
    if q.strip() or category.strip():
        stmt = stmt.limit(limit)

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
            rating=p.rating,
            discount_percent=p.discount_percent,
            original_price=p.original_price,
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
        rating=product.rating,
        discount_percent=product.discount_percent,
        original_price=product.original_price,
    )
