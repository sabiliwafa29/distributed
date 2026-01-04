from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class ProductBase(BaseModel):
    """Base schema for Product with common attributes."""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    price: float = Field(..., gt=0, description="Product price (must be positive)")
    stock: int = Field(..., ge=0, description="Available stock (must be non-negative)")


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating an existing product. All fields are optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    price: Optional[float] = Field(None, gt=0, description="Product price")
    stock: Optional[int] = Field(None, ge=0, description="Available stock")


class ProductResponse(ProductBase):
    """Schema for product response including all fields."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    """Schema for paginated product list response."""
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
