from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from datetime import datetime, time
import json
import os
from django.conf import settings
from django.http import JsonResponse
from menus.models import DiningHall
from recommendation import get_recommendations_for_all_dining
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import UserFoodPreference
from .forms import FoodPreferenceForm
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View


class RegisterView(CreateView):
    template_name = 'registration/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('login')

def home_view(request):
    return render(request, 'home.html')

def get_mock_dining_data():
    """Load dining hall data from JSON file"""
    try:
        halls = DiningHall.objects.all()
        response = []

        for hall in halls:
            response.append({
                "hallName": hall.hallName,
                "hours": hall.hours,
                "mealHours": hall.mealHours,
                "isOpen": is_hall_open(hall.hours),
                "meals": hall.meals or {"breakfast": [], "lunch": [], "dinner": []}
            })

        return response
    except FileNotFoundError:
        # Fallback data if JSON file is not found
        return [
            {
                "hallName": "Hamp",
                "hours": "07:00-20:00",
                "meals": {
                    "breakfast": ["Oatmeal", "Scrambled Eggs"],
                    "lunch": ["Veg Curry", "Rice"],
                    "dinner": ["Pasta", "Salad"]
                }
            }
        ]
    except (json.JSONDecodeError, KeyError) as e:
        # Return minimal data if JSON is malformed
        return [
            {
                "hallName": "Error",
                "hours": "00:00-00:00",
                "meals": {
                    "breakfast": ["Data loading error"],
                    "lunch": ["Please try again"],
                    "dinner": ["Contact support"]
                }
            }
        ]

def is_hall_open(hours_str):
    """Check if dining hall is currently open based on hours string"""
    try:
        # Parse hours like "07:00-20:00"
        start_str, end_str = hours_str.split('-')
        start_time = datetime.strptime(start_str, '%H:%M').time()
        end_time = datetime.strptime(end_str, '%H:%M').time()
        current_time = datetime.now().time()
        
        return start_time <= current_time <= end_time
    except:
        return False

@login_required
def menu_view(request):
    """Display dining halls with their menus and open/closed status"""
    try:
        dining_halls = get_mock_dining_data()
        
        # Add open/closed status to each hall
        for hall in dining_halls:
            hall['isOpen'] = is_hall_open(hall['hours'])
        
        context = {
            'dining_halls': dining_halls,
            'error': None
        }
    except Exception as e:
        context = {
            'dining_halls': [],
            'error': f"Error loading menu data: {str(e)}"
        }
    
    return render(request, 'menu.html', context)

@login_required
def api_menus_view(request):
    """API endpoint that returns dining hall data as JSON"""
    try:
        dining_halls = get_mock_dining_data()
        
        # Add open/closed status to each hall
        for hall in dining_halls:
            hall['isOpen'] = is_hall_open(hall['hours'])
        
        return JsonResponse(dining_halls, safe=False)
    except Exception as e:
        return JsonResponse({'error': f"Error loading menu data: {str(e)}"}, status=500)

def logout_then_login(request):
    """
    Logs the user out on GET and redirects to the login page.
    """
    logout(request)
    return redirect('login')

class RecommendView(LoginRequiredMixin, View):
    login_url = "/login/"  # optional
    redirect_field_name = "next"
    template_name = "recommend.html"

    def get(self, request):
        return render(request, self.template_name, {
            "preference": "",
            "recommendations": None,
            "error": None,
        })

    def post(self, request):
        preference = request.POST.get("preference", "").strip()

        recommendations = None
        error = None

        if preference:
            try:
                # Load saved preferences
                pref, _ = UserFoodPreference.objects.get_or_create(user=request.user)
                stored = pref.data or {}

                # Merge stored preferences + free-text input
                # Free text still goes to LLM — stored prefs override where needed
                recommendations = get_recommendations_for_all_dining(
                    mood_text=preference,
                    stored_preferences=stored
                )

            except Exception as e:
                error = str(e)

        context = {
            "preference": preference,
            "recommendations": recommendations,
            "error": error,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class UserPreferenceView(View):
    template_name = "preferences.html"

    def get(self, request):
        # Load user's existing preferences
        pref, _ = UserFoodPreference.objects.get_or_create(user=request.user)
        
        initial = pref.data if pref.data else {}
        form = FoodPreferenceForm(initial=initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = FoodPreferenceForm(request.POST)

        if form.is_valid():
            cleaned = form.cleaned_data

            # Save structured data exactly as lists / strings
            data = {
                "diet": cleaned["diet"],
                "avoid_allergens": cleaned["avoid_allergens"],
                "avoid_ingredients": cleaned["avoid_ingredients"],
                "goals": cleaned["goals"],
                "likes": cleaned["likes"],
                "dislikes": cleaned["dislikes"],
            }

            pref, _ = UserFoodPreference.objects.get_or_create(user=request.user)
            pref.data = data
            pref.save()

            return render(request, self.template_name, {
                "form": form,
                "success": "Preferences updated successfully!"
            })

        return render(request, self.template_name, {"form": form})

