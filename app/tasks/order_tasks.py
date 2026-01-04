import time
import logging
from celery import shared_task

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_order")
def process_order(self, order_id: int) -> dict:
    """
    Background task to process an order.
    
    This task simulates an external API call (e.g., payment processing,
    notification service, inventory sync) with a 5-second delay.
    
    In a real-world scenario, this could:
    - Call payment gateway API
    - Send confirmation email
    - Update external inventory system
    - Generate invoice
    - Notify shipping provider
    
    Args:
        order_id: ID of the order to process
        
    Returns:
        Dictionary with processing result
    """
    logger.info(f"Starting to process Order #{order_id}")
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Update order status to PROCESSING
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            logger.error(f"Order #{order_id} not found")
            return {"status": "failed", "error": "Order not found"}
        
        order.status = OrderStatus.PROCESSING
        db.commit()
        
        # Simulate external API call (5-second delay)
        logger.info(f"Order #{order_id} - Simulating external API call...")
        time.sleep(5)
        
        # Mark as completed
        order.status = OrderStatus.COMPLETED
        db.commit()
        
        # Log completion message as required
        logger.info(f"Order #{order_id} Processed.")
        print(f"Order #{order_id} Processed.")  # Also print for visibility
        
        return {
            "status": "success",
            "order_id": order_id,
            "message": f"Order #{order_id} Processed."
        }
        
    except Exception as e:
        logger.error(f"Error processing Order #{order_id}: {e}")
        
        # Mark order as failed
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = OrderStatus.FAILED
                db.commit()
        except:
            db.rollback()
        
        raise self.retry(exc=e, countdown=60, max_retries=3)
        
    finally:
        db.close()


@celery_app.task(bind=True, name="send_order_notification")
def send_order_notification(self, order_id: int, email: str = None) -> dict:
    """
    Send order notification (example additional task).
    
    Args:
        order_id: Order ID
        email: Customer email address
        
    Returns:
        Notification result
    """
    logger.info(f"Sending notification for Order #{order_id}")
    
    # Simulate sending email
    time.sleep(1)
    
    logger.info(f"Notification sent for Order #{order_id}")
    
    return {
        "status": "sent",
        "order_id": order_id,
        "email": email
    }
