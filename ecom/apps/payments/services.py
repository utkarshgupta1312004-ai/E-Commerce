import hmac
import hashlib
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings
try:
    import razorpay
    from razorpay.errors import SignatureVerificationError, BadRequestError, ServerError
except ImportError:
    razorpay = None
    class SignatureVerificationError(Exception):
        pass
    class BadRequestError(Exception):
        pass
    class ServerError(Exception):
        pass

logger = logging.getLogger(__name__)


class RazorpayServiceException(Exception):
    """Custom exception raised when Razorpay interaction encounters a failure."""
    def __init__(self, message: str, code: str = '', raw: Any = None):
        super().__init__(message)
        self.code = code
        self.raw = raw


class RazorpayService:
    """
    Production-grade integration service for Razorpay Payment Gateway.
    Encapsulates order creation, signature verification, payment fetching, and webhook handling.
    """

    @classmethod
    def get_key_id(cls) -> str:
        return getattr(settings, 'RAZORPAY_KEY_ID', '').strip()

    @classmethod
    def get_key_secret(cls) -> str:
        return getattr(settings, 'RAZORPAY_KEY_SECRET', '').strip()

    @classmethod
    def get_currency(cls) -> str:
        return getattr(settings, 'RAZORPAY_CURRENCY', 'INR').strip()

    @classmethod
    def get_webhook_secret(cls) -> str:
        return getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '').strip()

    @classmethod
    def is_configured(cls) -> bool:
        """Returns True if valid non-empty Razorpay keys are provided."""
        key_id = cls.get_key_id()
        key_secret = cls.get_key_secret()
        return bool(key_id and key_secret)

    @classmethod
    def is_test_mode(cls) -> bool:
        """Returns True if test credentials are used (rzp_test_...)."""
        return cls.get_key_id().startswith('rzp_test_')

    @classmethod
    def get_mode(cls) -> str:
        """Returns 'TEST', 'LIVE', or 'UNCONFIGURED'."""
        key_id = cls.get_key_id()
        if not key_id:
            return 'UNCONFIGURED'
        if key_id.startswith('rzp_test_'):
            return 'TEST'
        if key_id.startswith('rzp_live_'):
            return 'LIVE'
        return 'UNKNOWN'

    @classmethod
    def get_client(cls):
        """Instantiates and returns the official Razorpay client."""
        if razorpay is None:
            raise RazorpayServiceException(
                "The 'razorpay' package is not installed. Please install it using 'pip install razorpay'.",
                code="PACKAGE_MISSING"
            )

        key_id = cls.get_key_id()
        key_secret = cls.get_key_secret()

        if not key_id or not key_secret:
            raise RazorpayServiceException(
                "Razorpay API credentials (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET) are not configured in environment.",
                code="CONFIG_MISSING"
            )

        # Warn if Live credentials are used with DEBUG=True
        if getattr(settings, 'DEBUG', False) and key_id.startswith('rzp_live_'):
            logger.warning("SECURITY ALERT: Razorpay LIVE key is configured in development environment with DEBUG=True!")

        client = razorpay.Client(auth=(key_id, key_secret))
        client.set_app_details({"title": "Cartivo", "version": "2.0.0"})
        return client

    @classmethod
    def create_order(
        cls,
        amount: Decimal,
        currency: Optional[str] = None,
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay Order on the backend.
        
        Args:
            amount: Total order amount in decimal currency unit (e.g. INR 499.00).
            currency: ISO currency code (defaults to RAZORPAY_CURRENCY or 'INR').
            receipt: Internal transaction/order reference (max 40 chars).
            notes: Additional metadata key-values.
            
        Returns:
            Dict containing order details ('id', 'amount', 'currency', 'status', etc.)
        """
        import uuid
        import time

        curr = currency or cls.get_currency()
        amount_decimal = Decimal(str(amount))
        # Razorpay expects amounts in smallest currency subunits (paise for INR: 1 INR = 100 paise)
        amount_paise = int(round(amount_decimal * 100))

        if amount_paise <= 0:
            raise RazorpayServiceException("Order amount must be greater than zero.", code="INVALID_AMOUNT")

        # Sanitize receipt to max 40 chars
        clean_receipt = str(receipt or f"RCPT-{uuid.uuid4().hex[:12].upper()}").strip()[:40]

        # Sanitize notes: max 15 key-value pairs, string values <= 256 chars
        clean_notes = {}
        if notes and isinstance(notes, dict):
            for k, v in list(notes.items())[:15]:
                clean_notes[str(k)[:255]] = str(v)[:256]

        payload = {
            'amount': amount_paise,
            'currency': curr,
            'receipt': clean_receipt,
            'notes': clean_notes,
        }

        # Attempt creation; only retry transient network/server drops, NEVER retry authentication errors
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                client = cls.get_client()
                razorpay_order = client.order.create(data=payload)
                logger.info("Created Razorpay Order %s for amount %s %s (mode=%s)", razorpay_order.get('id'), amount_paise, curr, cls.get_mode())
                return razorpay_order
            except BadRequestError as exc:
                err_msg = str(exc)
                logger.error("Razorpay order creation bad request: %s", err_msg)
                if 'Authentication failed' in err_msg or 'expired' in err_msg.lower():
                    raise RazorpayServiceException(
                        "Gateway authentication failed. Please verify Razorpay API Key ID and Key Secret in server configuration.",
                        code="AUTH_FAILED",
                        raw=exc
                    )
                raise RazorpayServiceException(
                    f"Invalid order request to payment gateway: {err_msg}",
                    code="GATEWAY_BAD_REQUEST",
                    raw=exc
                )
            except ServerError as exc:
                err_msg = str(exc)
                logger.warning("Razorpay server error on attempt %d: %s", attempt + 1, err_msg)
                if attempt < max_retries:
                    time.sleep(0.5)
                    continue
                raise RazorpayServiceException(
                    "Payment gateway server is currently unavailable. Please try again or choose Cash on Delivery.",
                    code="GATEWAY_SERVER_ERROR",
                    raw=exc
                )
            except Exception as exc:
                logger.error("Unexpected error in create_order: %s", str(exc), exc_info=True)
                raise RazorpayServiceException(
                    "Payment gateway encountered an unexpected internal error.",
                    code="INTERNAL_ERROR",
                    raw=exc
                )

    @classmethod
    def verify_payment_signature(
        cls,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """
        Cryptographically verifies the HMAC SHA256 signature returned by Razorpay Checkout.
        Validates HMAC-SHA256(order_id + "|" + payment_id, key_secret) == razorpay_signature.
        Protects against payment tampering and replay attacks.
        
        Returns:
            True if signature is valid, False otherwise.
        """
        if not (razorpay_order_id and razorpay_payment_id and razorpay_signature):
            logger.warning("Missing required signature verification parameters.")
            return False

        order_id = razorpay_order_id.strip()
        payment_id = razorpay_payment_id.strip()
        signature = razorpay_signature.strip()
        secret = cls.get_key_secret()

        if not secret:
            logger.error("Signature verification failed: RAZORPAY_KEY_SECRET is not configured.")
            return False

        # 1. Primary verification via official Razorpay SDK utility
        try:
            client = cls.get_client()
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            client.utility.verify_payment_signature(params_dict)
            logger.info("Signature verification passed via Razorpay SDK for payment %s", payment_id)
            return True
        except SignatureVerificationError:
            logger.warning("SDK signature verification failed for Razorpay payment %s", payment_id)
        except Exception as exc:
            logger.warning("SDK signature verification exception: %s. Falling back to native HMAC verification.", str(exc))

        # 2. Timing-safe native HMAC SHA256 verification fallback
        try:
            message = f"{order_id}|{payment_id}".encode('utf-8')
            generated_signature = hmac.new(
                key=secret.encode('utf-8'),
                msg=message,
                digestmod=hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(generated_signature, signature):
                logger.info("Signature verification passed via native HMAC SHA256 for payment %s", payment_id)
                return True
            else:
                logger.warning("Cryptographic signature mismatch for Razorpay payment %s", payment_id)
                return False
        except Exception as exc:
            logger.error("Error during native HMAC signature verification: %s", str(exc), exc_info=True)
            return False

    @classmethod
    def fetch_payment(cls, razorpay_payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches payment object details directly from Razorpay.
        Useful for extracting payment instrument (UPI, Card, NetBanking, Wallet) and bank details.
        Does not raise exceptions on network or authentication failure; returns None safely.
        """
        if not razorpay_payment_id:
            return None

        try:
            client = cls.get_client()
            payment = client.payment.fetch(razorpay_payment_id.strip())
            return payment
        except Exception as exc:
            logger.warning("Failed to fetch Razorpay payment %s: %s", razorpay_payment_id, str(exc))
            return None

    @classmethod
    def verify_webhook_signature(
        cls,
        body: Any,
        signature: str,
        secret: Optional[str] = None
    ) -> bool:
        """
        Verifies the incoming webhook signature from Razorpay using HMAC SHA256.
        Timing-safe and rejects empty secrets or signatures.
        """
        webhook_secret = (secret or cls.get_webhook_secret()).strip()
        clean_sig = (signature or '').strip()

        if not webhook_secret or not clean_sig or not body:
            logger.warning("Webhook verification rejected: missing secret, signature, or body.")
            return False

        try:
            body_bytes = body.encode('utf-8') if isinstance(body, str) else bytes(body)
            expected_signature = hmac.new(
                key=webhook_secret.encode('utf-8'),
                msg=body_bytes,
                digestmod=hashlib.sha256
            ).hexdigest()

            is_valid = hmac.compare_digest(expected_signature, clean_sig)
            if is_valid:
                logger.info("Razorpay webhook signature verified successfully.")
            else:
                logger.warning("Razorpay webhook signature mismatch.")
            return is_valid
        except Exception as exc:
            logger.error("Exception during webhook signature verification: %s", str(exc), exc_info=True)
            return False

