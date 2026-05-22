from .models import UserProfile


def user_role(request):
    """Inject ``role`` into every template context automatically."""
    if not request.user.is_authenticated:
        return {'role': 'visiteur'}
    if request.user.is_superuser:
        return {'role': 'admin'}
    try:
        return {'role': request.user.profile.role}
    except UserProfile.DoesNotExist:
        return {'role': 'visiteur'}
