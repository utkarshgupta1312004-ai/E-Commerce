from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Notification


@login_required(login_url='accounts:login')
def notification_list_view(request):
    """
    Customer notifications inbox (/notifications/).
    Lists notifications strictly for the authenticated user.
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required(login_url='accounts:login')
@require_POST
def mark_notification_read_view(request, notification_id):
    """Marks a single notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'is_read': True})

    next_url = request.POST.get('next') or 'notifications:notification_list'
    return redirect(next_url)


@login_required(login_url='accounts:login')
@require_POST
def mark_all_notifications_read_view(request):
    """Marks all notifications as read for the authenticated user."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})

    return redirect('notifications:notification_list')
