from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Create a new product with name, price, and initial stock."
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new product.
    
    - **name**: Product name (required)
    - **price**: Product price, must be positive (required)
    - **stock**: Initial stock quantity, must be non-negative (required)
    """
    service = ProductService(db)
    product = service.create(product_data)
    return product


@router.get(
    "/",
    response_model=ProductListResponse,
    summary="List all products",
    description="Get a paginated list of all products with optional search."
)
def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by product name"),
    db: Session = Depends(get_db)
):
    """Get paginated list of products."""
    service = ProductService(db)
    products, total, total_pages = service.get_all(page, page_size, search)
    
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
    description="Get detailed information about a specific product. Results are cached in Redis."
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a product by ID.
    
    This endpoint uses Redis caching for improved performance.
    Cache TTL is 5 minutes by default.
    """
    service = ProductService(db)
    product = service.get_by_id(product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    return product


@router.get(
    "/{product_id}/cached",
    summary="Get product from cache",
    description="Get product details from Redis cache (or database if not cached)."
)
def get_product_cached(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Get product from cache.
    
    Returns cached data if available, otherwise fetches from database
    and caches the result.
    """
    service = ProductService(db)
    product_data = service.get_by_id_cached(product_id)
    
    if not product_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    return product_data


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    description="Update product details. Only provided fields will be updated."
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a product.
    
    Partial updates are supported - only include fields you want to change.
    Cache is automatically invalidated after update.
    """
    service = ProductService(db)
    product = service.update(product_id, product_data)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
    description="Delete a product by ID. Associated cache is also cleared."
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Delete a product."""
    service = ProductService(db)
    deleted = service.delete(product_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    return None
