from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    """
    Renders customer authentication login template.
    Handles standard customer credentials and Google OAuth entrypoint.
    """
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        # Authentication logic will hook into accounts.services.AuthService once User model is migrated
        messages.info(request, "Authentication service is currently in test mode.")
        return render(request, 'accounts/login.html')

    return render(request, 'accounts/login.html')
