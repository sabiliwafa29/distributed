from sqlalchemy import Column, Integer, String, Float, DateTime, CheckConstraint
from sqlalchemy.sql import func

from app.database import Base


class Product(Base):
    """
    Product model representing items available for sale.
    
    Attributes:
        id: Unique identifier for the product
        name: Product name
        price: Product price (must be positive)
        stock: Available quantity (must be non-negative)
        created_at: Timestamp when product was created
        updated_at: Timestamp when product was last updated
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Database-level constraints to ensure data integrity
    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('stock >= 0', name='check_stock_non_negative'),
    )
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', stock={self.stock})>"
