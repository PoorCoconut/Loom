from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.guests import GUEST_SESSION_SECONDS, create_guest, is_guest, purge_old_guests


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home:home')
    else:
        form = AuthenticationForm()
    form.fields['username'].widget.attrs.update({'placeholder': 'Your username', 'autocomplete': 'username', 'autofocus': True})
    form.fields['password'].widget.attrs.update({'placeholder': 'Your password', 'autocomplete': 'current-password'})
    return render(request, 'login/login.html', {'form': form})


@require_POST
def guest_view(request):
    """Read-only visit: no sign-up, no weaving, just Discover and reading."""
    try:
        purge_old_guests()
    except Exception:
        pass
    user = create_guest()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session.set_expiry(GUEST_SESSION_SECONDS)
    messages.info(request, 'Welcome, guest! You can read any published story. Create an account to weave your own.')
    return redirect('discover:discover')


def logout_view(request):
    if request.method == 'POST':
        guest = request.user if is_guest(request.user) else None
        logout(request)
        if guest:
            guest.delete()  # guest accounts are throwaway
        return redirect('login:login')
    return redirect('home:home')
