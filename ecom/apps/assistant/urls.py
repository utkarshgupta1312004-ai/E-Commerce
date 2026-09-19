from django.urls import path
from .views import AssistantMessageView

app_name = 'assistant'

urlpatterns = [
    path('message/', AssistantMessageView.as_view(), name='message'),
]
