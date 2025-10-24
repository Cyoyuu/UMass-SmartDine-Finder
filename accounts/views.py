from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import logout

class RegisterView(CreateView):
    template_name = 'registration/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('login')

def home_view(request):
    return render(request, 'home.html')

def menu_view(request):
    return render(request, 'menu.html')

def logout_then_login(request):
    """
    Logs the user out on GET and redirects to the login page.
    """
    logout(request)
    return redirect('login')