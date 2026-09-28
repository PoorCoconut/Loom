from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm
from .models import Profile


@login_required
def profile_view(request):
    profile, _ = Profile.all_objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profiles:profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profiles/profile.html', {'form': form, 'profile': profile})
