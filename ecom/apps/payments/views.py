import json
import logging
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from apps.accounts.models import Address
from apps.cart.models import Cart
from apps.cart.services import CartService
from apps.inventory.services import InsufficientStockError
from apps.orders.models import Order, DeliveryCheckpoint
from apps.orders.services import OrderService
from apps.notifications.services import notify_order_event

from .models import PaymentTransaction
from .services import RazorpayService, RazorpayServiceException

logger = logging.getLogger(__name__)


@login_required(login_url='accounts:login')
@require_POST
def create_razorpay_order_view(request):
    """
    API endpoint invoked by the checkout page before launching the Razorpay modal.
    1. Validates active cart items and strictly re-verifies stock availability.
    2. Recalculates order financials entirely server-side (never trusts client amount).
    3. Resolves and validates the shipping address (with ownership authorization).
    4. Reuses recent pending transaction for the same cart/amount if available (double-click protection).
    5. Creates a Razorpay Order via backend gateway API.
    6. Stores the payment transaction in the database with address and cart link.
    7. Returns only public order parameters to checkout.js (key_id, order_id, amount).
    """
    # Defensive merge of session cart if any exists
    CartService.merge_guest_cart(request, request.user)

    cart = Cart.objects.filter(user=request.user, status='ACTIVE').order_by('-updated_at').first()
    if not cart or cart.items.count() == 0:
        return JsonResponse({
            'success': False,
            'error': 'Your shopping cart is empty. Please add products before paying.'
        }, status=400)

    cart_items = list(cart.items.select_related('product', 'variant').all())
    if not cart_items:
        return JsonResponse({
            'success': False,
            'error': 'Your shopping cart is empty.'
        }, status=400)

    # Re-verify stock before taking payment
    for item in cart_items:
        product = item.product
        variant = item.variant
        qty = item.quantity

        if not product.is_active or product.status != 'ACTIVE':
            return JsonResponse({
                'success': False,
                'error': f"Product '{product.title}' is no longer available for purchase."
            }, status=400)

        avail = variant.available_stock if variant else product.total_available_stock
        if avail < qty:
            sku_name = variant.name if variant else product.title
            return JsonResponse({
                'success': False,
                'error': f"Insufficient stock for '{sku_name}'. Requested: {qty}, Available: {avail}."
            }, status=400)

    # Accept both Form-encoded and JSON payloads
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (ValueError, TypeError):
            data = {}
    else:
        data = request.POST

    # Resolve shipping address with ownership verification
    address_id = str(data.get('address_id', '')).strip()
    address = None

    if address_id and address_id != 'new':
        try:
            address = Address.objects.filter(id=int(address_id), user=request.user).first()
            if not address:
                return JsonResponse({
                    'success': False,
                    'error': 'Selected shipping address is invalid or does not belong to your account.'
                }, status=400)
        except (ValueError, TypeError):
            address = None

    # Fallback to existing default address if no explicit id was provided
    if not address and not address_id:
        address = Address.objects.filter(user=request.user, address_type='shipping').order_by('-is_default', '-created_at').first()

    if not address or address_id == 'new':
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        street_address = data.get('street_address', '').strip()
        apartment = data.get('apartment', '').strip()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        postal_code = data.get('postal_code', '').strip()
        country = data.get('country', 'India').strip()
        save_address = data.get('save_address') in ('on', 'true', True)

        if not (full_name and street_address and city and state and postal_code):
            return JsonResponse({
                'success': False,
                'error': 'Please provide all required shipping address fields.'
            }, status=400)

        address = Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            street_address=street_address,
            apartment=apartment,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            address_type='shipping',
            is_default=save_address and not Address.objects.filter(user=request.user, address_type='shipping').exists()
        )

    customer_notes = data.get('customer_notes', '').strip()
    request.session['checkout_shipping_address_id'] = address.id
    if customer_notes:
        request.session['checkout_customer_notes'] = customer_notes

    # Recalculate financial total strictly server-side from database
    subtotal = cart.subtotal
    shipping = Decimal('0.00')
    discount = Decimal('0.00')
    tax = Decimal('0.00')
    total = subtotal + shipping - discount + tax

    if total <= Decimal('0.00'):
        return JsonResponse({
            'success': False,
            'error': 'Invalid order total amount.'
        }, status=400)

    # Double-click / duplicate order protection: check for recent unexpired INITIATED transaction (< 15 mins)
    recent_cutoff = timezone.now() - timezone.timedelta(minutes=15)
    existing_txn = PaymentTransaction.objects.filter(
        user=request.user,
        cart=cart,
        status='INITIATED',
        amount=total,
        created_at__gte=recent_cutoff,
        razorpay_order_id__isnull=False
    ).exclude(razorpay_order_id='').order_by('-created_at').first()

    if existing_txn:
        # Update address and notes in case the customer edited them
        existing_txn.shipping_address = address
        existing_txn.customer_notes = customer_notes
        existing_txn.save(update_fields=['shipping_address', 'customer_notes', 'updated_at'])

        logger.info("Reusing recent uncompleted Razorpay order %s for user %s", existing_txn.razorpay_order_id, request.user.username)
        return JsonResponse({
            'success': True,
            'razorpay_order_id': existing_txn.razorpay_order_id,
            'razorpay_key_id': RazorpayService.get_key_id(),
            'amount': int(round(total * 100)),
            'currency': existing_txn.currency,
            'name': 'Cartivo Luxury & Essentials',
            'description': f"Order Checkout ({cart.total_items} items)",
            'transaction_id': existing_txn.transaction_id,
            'is_test_mode': RazorpayService.is_test_mode(),
            'prefill': {
                'name': address.full_name or request.user.get_full_name() or request.user.username,
                'email': request.user.email or '',
                'contact': address.phone or ''
            },
            'theme': {
                'color': '#2563eb'
            }
        })

    # Generate new internal tracking reference
    txn_id = PaymentTransaction.generate_transaction_id()

    try:
        # Create Razorpay Order with backend validation
        razorpay_order = RazorpayService.create_order(
            amount=total,
            currency=RazorpayService.get_currency(),
            receipt=txn_id,
            notes={
                'user_id': str(request.user.id),
                'username': str(request.user.username),
                'cart_id': str(cart.id),
                'txn_id': str(txn_id),
            }
        )

        # Record payment transaction in ledger with address and notes
        payment_txn = PaymentTransaction.objects.create(
            transaction_id=txn_id,
            user=request.user,
            cart=cart,
            shipping_address=address,
            customer_notes=customer_notes,
            amount=total,
            currency=RazorpayService.get_currency(),
            gateway='RAZORPAY',
            status='INITIATED',
            razorpay_order_id=razorpay_order['id'],
            raw_response=razorpay_order
        )

        return JsonResponse({
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': RazorpayService.get_key_id(),
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'name': 'Cartivo Luxury & Essentials',
            'description': f"Order Checkout ({cart.total_items} items)",
            'transaction_id': txn_id,
            'is_test_mode': RazorpayService.is_test_mode(),
            'prefill': {
                'name': address.full_name or request.user.get_full_name() or request.user.username,
                'email': request.user.email or '',
                'contact': address.phone or ''
            },
            'theme': {
                'color': '#2563eb'
            }
        })

    except RazorpayServiceException as exc:
        logger.error("Razorpay order creation failed: [%s] %s", exc.code, str(exc))
        if exc.code == 'AUTH_FAILED':
            user_msg = "Online payment gateway is temporarily unavailable. Please verify API keys in dashboard or choose Cash on Delivery (COD)."
        else:
            user_msg = "Payment gateway could not be initialized. Please try again or choose Cash on Delivery (COD)."
        return JsonResponse({
            'success': False,
            'error': user_msg
        }, status=400)
    except Exception as exc:
        logger.exception("Unexpected error in create_razorpay_order_view: %s", exc)
        return JsonResponse({
            'success': False,
            'error': "An unexpected error occurred while connecting to payment gateway. Please try again."
        }, status=500)


@login_required(login_url='accounts:login')
@require_POST
def verify_razorpay_payment_view(request):
    """
    Validates Razorpay payment signature and converts the cart into a completed Order.
    Executes in a safe concurrency-locked database transaction:
    1. Verifies HMAC-SHA256 signature from Razorpay.
    2. Verifies payment amount and order_id consistency.
    3. Atomically locks stock, deducts inventory, and creates permanent Order & OrderItems.
    4. Marks PaymentTransaction as SUCCESS and links to the Order.
    5. Marks Cart as CONVERTED.
    6. Returns order confirmation redirect URL.
    """
    # Accept both Form encoded and JSON body
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (ValueError, TypeError):
            data = {}
    else:
        data = request.POST

    razorpay_order_id = data.get('razorpay_order_id', '').strip()
    razorpay_payment_id = data.get('razorpay_payment_id', '').strip()
    razorpay_signature = data.get('razorpay_signature', '').strip()

    if not (razorpay_order_id and razorpay_payment_id and razorpay_signature):
        return JsonResponse({
            'success': False,
            'error': 'Missing required payment verification parameters.'
        }, status=400)

    # Locate the initiated payment transaction for the current authenticated user (IDOR prevention)
    payment_txn = PaymentTransaction.objects.filter(
        razorpay_order_id=razorpay_order_id,
        user=request.user
    ).first()

    if not payment_txn:
        logger.warning("Payment verification attempted with unknown/unauthorized order_id %s by user %s", razorpay_order_id, request.user.username)
        return JsonResponse({
            'success': False,
            'error': 'No matching payment transaction found for this order.'
        }, status=404)

    # Acquire row-level lock within an atomic block to prevent concurrent verification races
    with transaction.atomic():
        payment_txn = PaymentTransaction.objects.select_for_update().filter(id=payment_txn.id).first()
        if not payment_txn:
            return JsonResponse({'success': False, 'error': 'Payment transaction not found.'}, status=404)

        # Idempotency check: if already verified and order created (e.g. by webhook or duplicate request)
        if payment_txn.status == 'SUCCESS' and payment_txn.order:
            logger.info("Payment %s was already processed for order %s. Returning existing order.", razorpay_payment_id, payment_txn.order.order_number)
            request.session['last_order_number'] = payment_txn.order.order_number
            return JsonResponse({
                'success': True,
                'order_number': payment_txn.order.order_number,
                'redirect_url': reverse('orders:order_success', kwargs={'order_number': payment_txn.order.order_number})
            })

        # Cryptographic HMAC SHA256 Signature Verification
        is_valid = RazorpayService.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature
        )

        if not is_valid:
            payment_txn.status = 'FAILED'
            payment_txn.error_code = 'SIGNATURE_VERIFICATION_FAILED'
            payment_txn.error_description = 'Cryptographic signature mismatch received from gateway.'
            payment_txn.razorpay_payment_id = razorpay_payment_id
            payment_txn.razorpay_signature = razorpay_signature
            payment_txn.save(update_fields=['status', 'error_code', 'error_description', 'razorpay_payment_id', 'razorpay_signature', 'updated_at'])
            logger.warning("Payment signature verification failed for user %s on order %s", request.user.username, razorpay_order_id)
            return JsonResponse({
                'success': False,
                'error': 'Payment verification failed. Your payment could not be authenticated.'
            }, status=400)

        # Fetch extra payment instrument details from Razorpay (method, vpa, card, bank)
        payment_details = RazorpayService.fetch_payment(razorpay_payment_id) or {}
        
        # Verify amount & order_id consistency if payment object was fetched
        if payment_details:
            fetched_amount = payment_details.get('amount')
            expected_amount = int(round(payment_txn.amount * 100))
            if fetched_amount and fetched_amount != expected_amount:
                logger.error("Payment amount mismatch! Expected: %s, Fetched: %s", expected_amount, fetched_amount)
                payment_txn.status = 'FAILED'
                payment_txn.error_code = 'AMOUNT_MISMATCH'
                payment_txn.error_description = f"Amount mismatch: expected {expected_amount}, received {fetched_amount}."
                payment_txn.save()
                return JsonResponse({
                    'success': False,
                    'error': 'Payment verification failed due to amount discrepancy. Please contact support.'
                }, status=400)

            fetched_order_id = payment_details.get('order_id')
            if fetched_order_id and fetched_order_id != razorpay_order_id:
                logger.error("Payment order_id mismatch! Expected: %s, Fetched: %s", razorpay_order_id, fetched_order_id)
                payment_txn.status = 'FAILED'
                payment_txn.error_code = 'ORDER_ID_MISMATCH'
                payment_txn.save()
                return JsonResponse({
                    'success': False,
                    'error': 'Payment verification failed due to order reference mismatch.'
                }, status=400)

        instrument_method = payment_details.get('method', '')
        bank = payment_details.get('bank', '')
        wallet = payment_details.get('wallet', '')
        vpa = payment_details.get('vpa', '')

        # Resolve shipping address: prefer stored address on transaction, then session, then user default
        address = payment_txn.shipping_address
        if not address:
            address_id = request.session.get('checkout_shipping_address_id')
            if address_id:
                address = Address.objects.filter(id=address_id, user=request.user).first()
        if not address:
            address = Address.objects.filter(user=request.user, address_type='shipping').order_by('-is_default', '-created_at').first()

        if not address:
            payment_txn.status = 'FAILED'
            payment_txn.error_code = 'ADDRESS_MISSING'
            payment_txn.error_description = 'Shipping address missing during payment confirmation.'
            payment_txn.save()
            return JsonResponse({
                'success': False,
                'error': 'Shipping address could not be resolved. Please contact support.'
            }, status=400)

        customer_notes = payment_txn.customer_notes or request.session.get('checkout_customer_notes', '')

        try:
            # Atomically create order, deduct stock, and convert cart
            order = OrderService.create_razorpay_order(
                user=request.user,
                address=address,
                customer_notes=customer_notes
            )

            # Update PaymentTransaction record
            payment_txn.order = order
            payment_txn.status = 'SUCCESS'
            payment_txn.razorpay_payment_id = razorpay_payment_id
            payment_txn.razorpay_signature = razorpay_signature
            payment_txn.method = instrument_method
            payment_txn.bank = bank
            payment_txn.wallet = wallet
            payment_txn.vpa = vpa
            payment_txn.raw_response = payment_details or {'id': razorpay_payment_id, 'order_id': razorpay_order_id}
            payment_txn.save()

            # Set delivery defaults
            if not order.tracking_number:
                order.tracking_number = order.tracking_code
            if not order.current_location:
                order.current_location = 'Cartivo Central Fulfillment Hub'
            if not order.estimated_delivery_date:
                order.estimated_delivery_date = 'Within 2-4 Business Days'
            order.save(update_fields=['tracking_number', 'current_location', 'estimated_delivery_date'])

            # Create initial confirmed checkpoint
            DeliveryCheckpoint.objects.create(
                order=order,
                status='CONFIRMED',
                location=order.current_location,
                notes=f'Payment verified successfully via Razorpay ({instrument_method.upper() or "ONLINE"}). Order confirmed.'
            )

            # Store last order number in session for instant confirmation access
            request.session['last_order_number'] = order.order_number
            request.session.pop('checkout_shipping_address_id', None)
            request.session.pop('checkout_customer_notes', None)

            # Dispatch notification
            notify_order_event(order, 'ORDER_CONFIRMED')

            messages.success(request, f"🎉 Payment successful! Order {order.order_number} confirmed.")
            return JsonResponse({
                'success': True,
                'order_number': order.order_number,
                'redirect_url': reverse('orders:order_success', kwargs={'order_number': order.order_number})
            })

        except InsufficientStockError as exc:
            payment_txn.status = 'FAILED'
            payment_txn.error_code = 'STOCK_EXHAUSTED'
            payment_txn.error_description = str(exc)
            payment_txn.save()
            logger.error("Stock shortage during payment verification for user %s: %s", request.user.username, str(exc))
            return JsonResponse({
                'success': False,
                'error': f"Stock shortage occurred: {str(exc)}. Please contact support for an immediate refund."
            }, status=400)
        except Exception as exc:
            payment_txn.status = 'FAILED'
            payment_txn.error_code = 'ORDER_CREATION_FAILED'
            payment_txn.error_description = str(exc)
            payment_txn.save()
            logger.exception("Error creating order after payment verification: %s", exc)
            return JsonResponse({
                'success': False,
                'error': 'Payment completed but order finalization encountered an error. Our team has been notified. Please contact support.'
            }, status=500)


@login_required(login_url='accounts:login')
@require_POST
def record_payment_failure_view(request):
    """
    Records payment gateway failure or modal dismissal sent from the frontend.
    Transitions PaymentTransaction state to FAILED or CANCELLED.
    """
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (ValueError, TypeError):
            data = {}
    else:
        data = request.POST

    razorpay_order_id = data.get('razorpay_order_id', '').strip()
    reason = data.get('reason', 'FAILED').upper()  # FAILED or CANCELLED
    error_code = data.get('error_code', '')
    error_description = data.get('error_description', '')

    if not razorpay_order_id:
        return JsonResponse({'success': False, 'error': 'Missing razorpay_order_id.'}, status=400)

    payment_txn = PaymentTransaction.objects.filter(
        razorpay_order_id=razorpay_order_id,
        user=request.user
    ).first()

    if payment_txn and payment_txn.status not in ('SUCCESS',):
        payment_txn.status = 'CANCELLED' if reason == 'CANCELLED' else 'FAILED'
        if error_code:
            payment_txn.error_code = error_code[:100]
        if error_description:
            payment_txn.error_description = error_description
        payment_txn.save(update_fields=['status', 'error_code', 'error_description', 'updated_at'])
        logger.info("Recorded payment status [%s] for order %s (user %s)", payment_txn.status, razorpay_order_id, request.user.username)

    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def razorpay_webhook_view(request):
    """
    Handles asynchronous webhook notifications dispatched by Razorpay.
    Mandatory cryptographic verification of X-Razorpay-Signature against RAZORPAY_WEBHOOK_SECRET.
    Processes:
      - payment.captured
      - payment.failed
      - order.paid
    Guarantees idempotency and creates orders if customer dropped connection during checkout.
    """
    webhook_secret = RazorpayService.get_webhook_secret()
    signature = request.headers.get('X-Razorpay-Signature', '').strip()

    if not webhook_secret:
        logger.error("Razorpay webhook received but RAZORPAY_WEBHOOK_SECRET is not configured.")
        return HttpResponse("Webhook secret unconfigured", status=500)

    if not signature:
        logger.warning("Razorpay webhook rejected: missing X-Razorpay-Signature header.")
        return HttpResponseBadRequest("Missing signature header")

    is_valid = RazorpayService.verify_webhook_signature(
        body=request.body,
        signature=signature,
        secret=webhook_secret
    )
    if not is_valid:
        logger.warning("Razorpay webhook signature verification failed.")
        return HttpResponseBadRequest("Invalid signature")

    try:
        payload = json.loads(request.body.decode('utf-8'))
        event = payload.get('event', '')
        payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
        order_entity = payload.get('payload', {}).get('order', {}).get('entity', {})

        razorpay_order_id = payment_entity.get('order_id') or order_entity.get('id') or ''
        razorpay_payment_id = payment_entity.get('id', '')

        logger.info("Received verified Razorpay webhook event: %s for order %s (payment %s)", event, razorpay_order_id, razorpay_payment_id)

        if not razorpay_order_id:
            return HttpResponse(status=200)

        with transaction.atomic():
            txn = PaymentTransaction.objects.select_for_update().filter(razorpay_order_id=razorpay_order_id).first()
            if not txn:
                logger.warning("Webhook received for unknown razorpay_order_id: %s", razorpay_order_id)
                return HttpResponse(status=200)

            if event in ('payment.captured', 'order.paid'):
                # If transaction is already successful and order exists, idempotently acknowledge
                if txn.status == 'SUCCESS' and txn.order:
                    logger.info("Webhook duplicate check: transaction %s is already processed for order %s", txn.transaction_id, txn.order.order_number)
                    return HttpResponse(status=200)

                # If order does not exist yet (e.g. browser dropped connection), create it now
                if txn.order is None and txn.cart and txn.cart.status == 'ACTIVE':
                    address = txn.shipping_address
                    if not address:
                        address = Address.objects.filter(user=txn.user, address_type='shipping').order_by('-is_default', '-created_at').first()

                    if address:
                        try:
                            order = OrderService.create_razorpay_order(
                                user=txn.user,
                                address=address,
                                customer_notes=txn.customer_notes
                            )
                            txn.order = order

                            if not order.tracking_number:
                                order.tracking_number = order.tracking_code
                            if not order.current_location:
                                order.current_location = 'Cartivo Central Fulfillment Hub'
                            if not order.estimated_delivery_date:
                                order.estimated_delivery_date = 'Within 2-4 Business Days'
                            order.save(update_fields=['tracking_number', 'current_location', 'estimated_delivery_date'])

                            DeliveryCheckpoint.objects.create(
                                order=order,
                                status='CONFIRMED',
                                location=order.current_location,
                                notes=f'Payment verified asynchronously via Webhook ({payment_entity.get("method", "ONLINE").upper()}). Order confirmed.'
                            )
                            notify_order_event(order, 'ORDER_CONFIRMED')
                            logger.info("Webhook created order %s for transaction %s", order.order_number, txn.transaction_id)
                        except Exception as exc:
                            logger.exception("Webhook order creation failed: %s", exc)

                txn.status = 'SUCCESS'
                txn.razorpay_payment_id = razorpay_payment_id or txn.razorpay_payment_id
                txn.method = payment_entity.get('method', txn.method)
                txn.raw_response = payload
                txn.save()

            elif event == 'payment.failed':
                if txn.status != 'SUCCESS':
                    txn.status = 'FAILED'
                    txn.error_code = payment_entity.get('error_code', 'PAYMENT_FAILED')
                    txn.error_description = payment_entity.get('error_description', 'Payment failed on gateway.')
                    txn.raw_response = payload
                    txn.save()

        return HttpResponse(status=200)
    except Exception as exc:
        logger.exception("Error processing Razorpay webhook: %s", exc)
        return HttpResponse(status=500)


@login_required(login_url='accounts:login')
@require_GET
def payment_transactions_view(request):
    """
    Customer portal view listing their own payment transactions and gateway records.
    Strictly isolated to request.user (IDOR protection).
    """
    transactions_list = PaymentTransaction.objects.filter(user=request.user).select_related('order').order_by('-created_at')
    return render(request, 'payments/transactions.html', {'transactions': transactions_list})
