from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    """Schema for creating a new order (purchase)."""
    product_id: int = Field(..., description="ID of the product to purchase")
    quantity: int = Field(default=1, ge=1, description="Quantity to purchase")


class OrderResponse(BaseModel):
    """Schema for order response."""
    id: int
    product_id: int
    quantity: int
    total_price: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    """Schema for paginated order list response."""
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderWithProduct(OrderResponse):
    """Schema for order response including product details."""
    product_name: Optional[str] = None
