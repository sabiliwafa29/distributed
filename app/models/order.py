from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class OrderStatus(str, enum.Enum):
    """Enum for order status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Order(Base):
    """
    Order model representing a purchase transaction.
    
    Attributes:
        id: Unique identifier for the order
        product_id: Reference to the purchased product
        quantity: Number of items purchased
        total_price: Total price for the order
        status: Current status of the order
        created_at: Timestamp when order was created
        updated_at: Timestamp when order was last updated
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    total_price = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to Product
    product = relationship("Product", backref="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, product_id={self.product_id}, status='{self.status}')>"
