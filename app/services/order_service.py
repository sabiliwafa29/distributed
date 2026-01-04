from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Tuple
import math
import logging

from app.models.product import Product
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate
from app.utils.cache import cache_service

logger = logging.getLogger(__name__)


class InsufficientStockError(Exception):
    """Exception raised when there's not enough stock to fulfill an order."""
    pass


class ProductNotFoundError(Exception):
    """Exception raised when the requested product doesn't exist."""
    pass


class OrderService:
    """
    Service class for Order operations with race condition handling.
    
    RACE CONDITION HANDLING STRATEGY:
    =================================
    We use PostgreSQL's SELECT FOR UPDATE with NOWAIT to handle concurrent 
    purchases of the same product. This approach:
    
    1. Acquires a row-level lock on the product when reading
    2. Prevents other transactions from modifying the same row
    3. Ensures atomic check-and-update of stock
    
    When multiple users try to buy the last item simultaneously:
    - First transaction acquires the lock and proceeds
    - Second transaction either waits (FOR UPDATE) or fails immediately (FOR UPDATE NOWAIT)
    - After first transaction commits, second transaction sees updated stock
    - Second transaction fails due to insufficient stock
    
    This is a pessimistic locking strategy, which is appropriate for:
    - High contention scenarios (popular products, flash sales)
    - When data consistency is critical
    - When conflicts are expected to be common
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_order(self, order_data: OrderCreate) -> Order:
        """
        Create a new order with atomic stock reservation.
        
        This method handles race conditions using pessimistic locking.
        
        Algorithm:
        1. Start transaction (implicit with SQLAlchemy)
        2. SELECT product FOR UPDATE (locks the row)
        3. Check if sufficient stock available
        4. Deduct stock and create order
        5. Commit transaction (releases lock)
        
        Args:
            order_data: Order creation data with product_id and quantity
            
        Returns:
            Created order instance
            
        Raises:
            ProductNotFoundError: If product doesn't exist
            InsufficientStockError: If not enough stock available
        """
        product_id = order_data.product_id
        quantity = order_data.quantity
        
        try:
            # Use FOR UPDATE to lock the product row
            # This prevents other transactions from modifying this product
            # until our transaction completes
            product = (
                self.db.query(Product)
                .filter(Product.id == product_id)
                .with_for_update()  # Pessimistic locking
                .first()
            )
            
            if not product:
                raise ProductNotFoundError(f"Product with ID {product_id} not found")
            
            # Check stock availability (inside the lock)
            if product.stock < quantity:
                raise InsufficientStockError(
                    f"Insufficient stock. Available: {product.stock}, Requested: {quantity}"
                )
            
            # Calculate total price
            total_price = product.price * quantity
            
            # Deduct stock (atomic operation within transaction)
            product.stock -= quantity
            
            # Create order
            order = Order(
                product_id=product_id,
                quantity=quantity,
                total_price=total_price,
                status=OrderStatus.PENDING
            )
            
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            
            # Invalidate product cache since stock changed
            cache_service.delete("product", str(product_id))
            
            logger.info(f"Order #{order.id} created successfully for product #{product_id}")
            
            return order
            
        except (ProductNotFoundError, InsufficientStockError):
            self.db.rollback()
            raise
        except IntegrityError as e:
            # Handle constraint violations (e.g., stock going negative)
            self.db.rollback()
            logger.error(f"Integrity error creating order: {e}")
            raise InsufficientStockError("Stock constraint violated - concurrent modification detected")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating order: {e}")
            raise
    
    def create_order_optimistic(self, order_data: OrderCreate) -> Order:
        """
        Alternative: Create order using optimistic locking with version check.
        
        This approach uses UPDATE with WHERE clause to atomically check and update.
        If the stock has changed since we read it, the UPDATE affects 0 rows.
        
        Pros:
        - No explicit locking, better for low-contention scenarios
        - Allows higher concurrency
        
        Cons:
        - May require retries
        - Not suitable for very high contention
        
        Args:
            order_data: Order creation data
            
        Returns:
            Created order instance
        """
        product_id = order_data.product_id
        quantity = order_data.quantity
        
        # First, get product info (without lock)
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            raise ProductNotFoundError(f"Product with ID {product_id} not found")
        
        # Attempt atomic update with condition
        # This UPDATE will only succeed if stock >= quantity
        result = self.db.execute(
            text("""
                UPDATE products 
                SET stock = stock - :quantity,
                    updated_at = NOW()
                WHERE id = :product_id 
                AND stock >= :quantity
            """),
            {"product_id": product_id, "quantity": quantity}
        )
        
        if result.rowcount == 0:
            self.db.rollback()
            raise InsufficientStockError(
                f"Insufficient stock or concurrent modification for product {product_id}"
            )
        
        # Create order
        order = Order(
            product_id=product_id,
            quantity=quantity,
            total_price=product.price * quantity,
            status=OrderStatus.PENDING
        )
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        # Invalidate cache
        cache_service.delete("product", str(product_id))
        
        return order
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Get an order by ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_orders(
        self, 
        page: int = 1, 
        page_size: int = 10,
        status: OrderStatus = None
    ) -> Tuple[List[Order], int, int]:
        """
        Get paginated list of orders.
        
        Args:
            page: Page number
            page_size: Items per page
            status: Filter by order status
            
        Returns:
            Tuple of (orders list, total count, total pages)
        """
        query = self.db.query(Order)
        
        if status:
            query = query.filter(Order.status == status)
        
        total = query.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        offset = (page - 1) * page_size
        orders = query.order_by(Order.id.desc()).offset(offset).limit(page_size).all()
        
        return orders, total, total_pages
    
    def update_status(self, order_id: int, status: OrderStatus) -> Optional[Order]:
        """Update order status."""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            return None
        
        order.status = status
        self.db.commit()
        self.db.refresh(order)
        
        return order
