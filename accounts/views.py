from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.shortcuts import render, redirect
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from menus.models import UserProfile, ALLERGEN_CHOICES, DIET_CHOICES, MealHistory
from datetime import datetime
import json


class RegisterView(CreateView):
    """User registration view - redirects to home after registration (with onboarding guide)."""
    template_name = 'registration/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('home')  # Fallback URL
    
    def form_valid(self, form):
        # Save the user (without calling super which would redirect)
        user = form.save()
        # Log the user in
        login(self.request, user)
        # Redirect to home (onboarding will guide to preferences)
        return redirect('home')


def home_view(request):
    """Home page view with dining hall data from database."""
    from menus.models import DiningHall
    import random
    import json
    
    # Limit number of dishes per meal type for visualization
    MAX_DISHES_PER_MEAL = 15
    
    # Load all dining halls from database
    db_halls = DiningHall.objects.all()
    
    # Build dining hall data structure for JavaScript
    dining_hall_data = {}
    
    for hall in db_halls:
        hall_key = hall.hallName.lower()
        meals = hall.meals or {"breakfast": [], "lunch": [], "dinner": []}
        
        # Convert to format expected by frontend
        dining_hall_data[hall_key] = {
            'breakfast': [],
            'lunch': [],
            'dinner': []
        }
        
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            items = meals.get(meal_type, [])
            
            # Convert items to the format needed
            converted_items = []
            for item in items:
                if isinstance(item, dict):
                    converted_items.append({
                        'name': item.get('name', 'Unknown'),
                        'count': item.get('weeklySelections', random.randint(100, 500)),
                        'calories': item.get('calories', 0),
                        'preferences': item.get('dietCategories', []),
                        'ingredients': item.get('ingredients', ''),
                        'allergens': item.get('allergens', [])
                    })
            
            # Sort by popularity (count/weeklySelections) and take top 15
            converted_items.sort(key=lambda x: x['count'], reverse=True)
            dining_hall_data[hall_key][meal_type] = converted_items[:MAX_DISHES_PER_MEAL]
    
    # Convert to JSON string for JavaScript
    dining_hall_data_json = json.dumps(dining_hall_data)
    
    context = {
        'dining_hall_data': dining_hall_data_json,
        'dining_halls_list': [hall.hallName for hall in db_halls]
    }
    
    return render(request, 'home.html', context)


@login_required
def survey_view(request):
    """Survey page for collecting user dietary preferences."""
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Get form data
        allergens = request.POST.getlist('allergens')
        calorie_target = request.POST.get('calorieTarget', 2000)
        diet_preferences = request.POST.getlist('dietPreferences')
        
        # Check if preferences changed (compare with existing profile)
        old_allergens = sorted(profile.allergens or [])
        old_diet_preferences = sorted(profile.dietPreferences or [])
        new_allergens = sorted(allergens)
        new_diet_preferences = sorted(diet_preferences)
        
        allergens_changed = old_allergens != new_allergens
        diet_preferences_changed = old_diet_preferences != new_diet_preferences
        
        # Update profile
        profile.allergens = allergens
        profile.calorieTarget = int(calorie_target) if calorie_target else 2000
        profile.dietPreferences = diet_preferences
        profile.surveyCompleted = True
        profile.save()
        
        # If preferences changed, clear today's selection from database
        if allergens_changed or diet_preferences_changed:
            today = datetime.now().date()
            MealHistory.objects.filter(user=request.user, date=today).delete()
        
        # Redirect to recommendations page
        return redirect('recommendations')
    
    # Convert preferences to JSON strings for JavaScript
    context = {
        'profile': profile,
        'allergen_choices': ALLERGEN_CHOICES,
        'diet_choices': DIET_CHOICES,
        'profile_allergens_json': json.dumps(profile.allergens or []),
        'profile_diet_preferences_json': json.dumps(profile.dietPreferences or []),
    }
    return render(request, 'registration/survey.html', context)


@login_required
def skip_survey(request):
    """Skip survey and go directly to recommendations."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    profile.surveyCompleted = True
    profile.save()
    return redirect('recommendations')


def logout_then_login(request):
    """Logs the user out and redirects to the login page."""
    logout(request)
    return redirect('login')
