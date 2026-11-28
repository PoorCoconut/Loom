from django.shortcuts import render, redirect
from django.contrib.auth import login

from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegisterForm


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            nxt = request.GET.get('next', '')
            ok = url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure())
            return redirect(nxt if ok else 'home:home')
    else:
        form = RegisterForm()
    return render(request, 'register/register.html', {'form': form, 'next': request.GET.get('next', '')})
