from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.order_service import (
    OrderService,
    InsufficientStockError,
    ProductNotFoundError
)
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderListResponse
)
from app.models.order import OrderStatus
from app.tasks.order_tasks import process_order

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order (purchase)",
    description="""
    Purchase a product by creating an order.
    
    **Race Condition Handling:**
    This endpoint uses PostgreSQL's SELECT FOR UPDATE to prevent overselling.
    When multiple users try to buy the last item simultaneously:
    - Only one transaction succeeds
    - Others receive a 400 error with 'Insufficient stock' message
    
    After successful order creation, a background Celery task is triggered
    to process the order (simulating external API calls).
    """
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db)
):
    """
    Create a purchase order.
    
    - **product_id**: ID of the product to purchase (required)
    - **quantity**: Number of items to buy, default is 1 (optional)
    
    The order goes through these states:
    1. PENDING - Order created, waiting for processing
    2. PROCESSING - Background task is processing the order
    3. COMPLETED - Order fully processed
    4. FAILED - Order processing failed
    """
    service = OrderService(db)
    
    try:
        order = service.create_order(order_data)
        
        # Trigger background task to process the order
        process_order.delay(order.id)
        
        return order
        
    except ProductNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=OrderListResponse,
    summary="List all orders",
    description="Get a paginated list of orders with optional status filter."
)
def list_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    db: Session = Depends(get_db)
):
    """Get paginated list of orders."""
    service = OrderService(db)
    orders, total, total_pages = service.get_orders(page, page_size, status)
    
    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
    description="Get detailed information about a specific order."
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Get an order by ID."""
    service = OrderService(db)
    order = service.get_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )
    
    return order


@router.get(
    "/{order_id}/status",
    summary="Get order status",
    description="Get the current status of an order and its Celery task."
)
def get_order_status(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Get order processing status.
    
    Returns both the database status and Celery task status if available.
    """
    service = OrderService(db)
    order = service.get_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )
    
    return {
        "order_id": order.id,
        "status": order.status,
        "created_at": order.created_at,
        "updated_at": order.updated_at
    }
