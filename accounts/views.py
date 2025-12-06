from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.shortcuts import render, redirect
from django.contrib.auth import logout


class RegisterView(CreateView):
    """User registration view."""
    template_name = 'registration/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('login')


def home_view(request):
    """Home page view."""
    return render(request, 'home.html')


def logout_then_login(request):
    """Logs the user out and redirects to the login page."""
    logout(request)
    return redirect('login')
