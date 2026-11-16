from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.profiles.models import Profile

from .forms import UserSettingsForm
from .models import UserSettings


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    profile = Profile.all_objects.filter(user=request.user).first()

    if request.method == 'POST' and request.POST.get('action') == 'deactivate':
        if request.POST.get('confirm', '').strip() == request.user.get_username():
            (profile or Profile.all_objects.create(user=request.user)).delete()  # soft delete + blocks login
            logout(request)
            return redirect('login:login')
        messages.error(request, 'Type your username exactly to deactivate your account.')
        return redirect('user_settings:settings')

    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings saved. Your weave screen will use them right away.')
            return redirect('user_settings:settings')
    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, 'user_settings/settings.html', {
        'form': form, 'settings': settings_obj, 'view': 'settings',
        'nav_avatar': getattr(profile, 'avatar_url', None),
        'sizes': UserSettings.READER_SIZES, 'fonts': UserSettings.FONTS,
    })
