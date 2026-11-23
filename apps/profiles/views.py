from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.core.guests import is_guest
from apps.editor.models import Node
from apps.stories.models import Story

from .forms import ProfileForm
from .models import Profile


@login_required
def profile_view(request):
    if is_guest(request.user):
        messages.info(request, "Guests don't have a profile. Create an account to get one.")
        return redirect('discover:discover')
    profile, _ = Profile.all_objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been saved.')
            return redirect('profiles:profile')
    else:
        form = ProfileForm(instance=profile)

    mine = Story.objects.filter(author=request.user)
    stats = {
        'stories': mine.count(),
        'published': mine.filter(is_published=True).count(),
        'scenes': Node.objects.filter(story__in=mine).count(),
    }
    return render(request, 'profiles/profile.html', {
        'form': form, 'profile': profile, 'stats': stats,
        'view': 'profile', 'nav_avatar': profile.avatar_url,
    })
