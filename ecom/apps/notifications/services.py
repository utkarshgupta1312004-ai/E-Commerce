from typing import Optional
from django.urls import reverse
from .models import Notification


def notify_order_event(order, event_type: str, custom_message: Optional[str] = None) -> Optional[Notification]:
    """
    Dispatches a customer-safe notification on shipping or payment events (Requirements 58 & 59).
    Strictly scoped to the customer who placed this order (order.user).
    Never exposes another customer's data.
    """
    if not order or not getattr(order, 'user', None):
        return None

    # Customer notification templates matching Requirement 58
    templates = {
        'ORDER_CONFIRMED': {
            'title': f"Order #{order.order_number} Confirmed",
            'message': f"Your order {order.order_number} has been confirmed.",
        },
        'ORDER_PACKED': {
            'title': f"Order #{order.order_number} Packed",
            'message': f"Your order {order.order_number} has been packed.",
        },
        'ORDER_SHIPPED': {
            'title': f"Order #{order.order_number} Shipped",
            'message': f"Your order {order.order_number} has been shipped.",
        },
        'OUT_FOR_DELIVERY': {
            'title': f"Order #{order.order_number} Out for Delivery",
            'message': f"Your order {order.order_number} is out for delivery.",
        },
        'ORDER_DELIVERED': {
            'title': f"Order #{order.order_number} Delivered",
            'message': f"Your order {order.order_number} has been delivered.",
        },
        'COD_PAYMENT_RECEIVED': {
            'title': f"COD Payment Received - #{order.order_number}",
            'message': f"COD payment of ₹{order.total_amount} has been received.",
        },
        'ORDER_COMPLETED': {
            'title': f"Order #{order.order_number} Completed",
            'message': f"Your order {order.order_number} is completed.",
        },
        'DELIVERY_FAILED': {
            'title': f"Delivery Unsuccessful - #{order.order_number}",
            'message': f"Delivery attempt for order {order.order_number} was unsuccessful.",
        },
        'ORDER_RETURNED': {
            'title': f"Order #{order.order_number} Returned",
            'message': f"Your order {order.order_number} has been returned.",
        },
        'ORDER_CANCELLED': {
            'title': f"Order #{order.order_number} Cancelled",
            'message': f"Your order {order.order_number} has been cancelled.",
        },
    }

    config = templates.get(event_type, {
        'title': f"Update on Order #{order.order_number}",
        'message': f"Update on order {order.order_number}.",
    })

    title = config['title']
    message = custom_message or config['message']
    link = reverse('orders:order_detail', kwargs={'order_number': order.order_number})

    notification = Notification.objects.create(
        user=order.user,
        order=order,
        event_type=event_type,
        title=title,
        message=message,
        link=link
    )
    return notification
