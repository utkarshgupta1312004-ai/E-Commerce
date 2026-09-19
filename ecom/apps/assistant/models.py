import uuid
from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """
    Stores an ongoing conversation session with the AI shopping concierge.
    Associates with an authenticated user or a guest browser session.
    """
    session_id = models.CharField(max_length=64, unique=True, db_index=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_sessions',
        help_text="Authenticated customer or staff user (null for guest shoppers)"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Session metadata such as initial landing page, device info, active cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'
        ordering = ['-updated_at']

    def __str__(self):
        user_display = self.user.username if self.user else "Guest"
        return f"ChatSession {self.session_id[:8]}... ({user_display})"


class ChatMessage(models.Model):
    """
    Individual message turn in a ChatSession, including tool invocations,
    execution results, and client UI actions triggered.
    """
    SENDER_USER = 'user'
    SENDER_ASSISTANT = 'assistant'
    SENDER_SYSTEM = 'system'

    SENDER_CHOICES = (
        (SENDER_USER, 'User'),
        (SENDER_ASSISTANT, 'Assistant'),
        (SENDER_SYSTEM, 'System'),
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES, default=SENDER_USER)
    text = models.TextField(blank=True, default="")
    raw_tool_calls = models.JSONField(
        default=list,
        blank=True,
        help_text="Raw tool function call requests emitted by Gemini"
    )
    raw_tool_results = models.JSONField(
        default=list,
        blank=True,
        help_text="Raw backend execution results returned to Gemini"
    )
    actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Deterministic UI actions dispatched to the browser frontend"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.sender}: {self.text[:40]}"
