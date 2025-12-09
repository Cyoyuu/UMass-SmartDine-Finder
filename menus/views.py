from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
import json
import os
import copy
from django.conf import settings
from .models import DiningHall, Review, UserProfile, MealHistory, ALLERGEN_CHOICES, DIET_CHOICES
from recommendation import get_recommendations_for_all_dining


# ============== Load Menu Data from Database ==============

def get_menu_data_from_db():
    """Load dining hall menu data from database."""
    try:
        halls = DiningHall.objects.all()
        dining_halls = []
        
        for hall in halls:
            dining_halls.append({
                "id": hall.id,
                "hallName": hall.hallName,
                "hours": hall.hours,
                "mealHours": hall.mealHours,
                "meals": hall.meals or {"breakfast": [], "lunch": [], "dinner": []}
            })
        
        return {
            "diningHalls": dining_halls,
            "allergenCategories": [
                {'id': 'dairy', 'name': 'Dairy', 'icon': '🥛'},
                {'id': 'eggs', 'name': 'Eggs', 'icon': '🥚'},
                {'id': 'fish', 'name': 'Fish', 'icon': '🐟'},
                {'id': 'shellfish', 'name': 'Shellfish', 'icon': '🦐'},
                {'id': 'tree_nuts', 'name': 'Tree Nuts', 'icon': '🌰'},
                {'id': 'peanuts', 'name': 'Peanuts', 'icon': '🥜'},
                {'id': 'gluten', 'name': 'Gluten', 'icon': '🌾'},
                {'id': 'soy', 'name': 'Soy', 'icon': '🫘'},
                {'id': 'sesame', 'name': 'Sesame', 'icon': '⚪'},
                {'id': 'corn', 'name': 'Corn', 'icon': '🌽'},
            ],
            "dietCategories": [
                {'id': 'vegetarian', 'name': 'Vegetarian', 'icon': '🥬'},
                {'id': 'local', 'name': 'Local', 'icon': '📍'},
                {'id': 'sustainable', 'name': 'Sustainable', 'icon': '♻️'},
                {'id': 'whole_grain', 'name': 'Whole Grain', 'icon': '🌾'},
                {'id': 'halal', 'name': 'Halal', 'icon': '☪️'},
                {'id': 'antibiotic_free', 'name': 'Antibiotic Free', 'icon': '💊'},
                {'id': 'plant_based', 'name': 'Plant Based', 'icon': '🌱'},
            ]
        }
    except Exception as e:
        print(f"Error loading menu data from database: {e}")
        return {"diningHalls": [], "allergenCategories": [], "dietCategories": []}


# Cache the menu data
_cached_menu_data = None

def get_menu_data():
    """Get cached menu data or load from database."""
    global _cached_menu_data
    if _cached_menu_data is None:
        _cached_menu_data = get_menu_data_from_db()
    return _cached_menu_data


def clear_menu_cache():
    """Clear the menu data cache to force reload from database."""
    global _cached_menu_data
    _cached_menu_data = None


def is_hall_open(hours_str):
    """Check if dining hall is currently open based on hours string."""
    try:
        start_str, end_str = hours_str.split('-')
        start_time = datetime.strptime(start_str, '%H:%M').time()
        end_time = datetime.strptime(end_str, '%H:%M').time()
        current_time = datetime.now().time()
        return start_time <= current_time <= end_time
    except Exception:
        return False


def is_weekend():
    """Check if today is Saturday or Sunday."""
    return datetime.now().weekday() >= 5  # 5 = Saturday, 6 = Sunday


def get_current_meal_type():
    """Get current meal type based on time. Returns lunch if weekend and before 15:00."""
    now = datetime.now()
    current_time = now.time()
    
    # No breakfast on weekends
    if is_weekend():
        if current_time < datetime.strptime("15:00", "%H:%M").time():
            return "lunch"
        else:
            return "dinner"
    
    # Weekday logic
    if current_time < datetime.strptime("10:30", "%H:%M").time():
        return "breakfast"
    elif current_time < datetime.strptime("15:00", "%H:%M").time():
        return "lunch"
    else:
        return "dinner"


def filter_meals_for_user(meals, user_allergens=None, user_diet_prefs=None):
    """Filter meals based on user preferences."""
    filtered = {"breakfast": [], "lunch": [], "dinner": []}
    
    for meal_type in ["breakfast", "lunch", "dinner"]:
        items = meals.get(meal_type, [])
        for item in items:
            # Handle both old format (string) and new format (dict)
            if isinstance(item, str):
                filtered[meal_type].append({
                    "name": item,
                    "calories": 0,
                    "allergens": [],
                    "dietCategories": [],
                    "ingredients": "",
                    "weeklySelections": 0
                })
            else:
                # Check allergens - skip items containing user's allergens
                item_allergens = item.get("allergens", [])
                if user_allergens and any(a in item_allergens for a in user_allergens):
                    continue  # Skip items with user's allergens
                
                filtered[meal_type].append(item)
    
    return filtered


def calculate_hall_score(hall_data, user_allergens=None, user_diet_prefs=None):
    """Calculate recommendation score for a dining hall."""
    score = 0
    total_items = 0
    total_matching_items = 0
    total_calories = 0
    preference_matches = 0
    
    meals = hall_data.get("meals", {})
    current_meal = get_current_meal_type()
    
    for meal_type in ["breakfast", "lunch", "dinner"]:
        items = meals.get(meal_type, [])
        for item in items:
            total_items += 1
            
            if isinstance(item, dict):
                # Check allergens - skip if has user's allergens
                item_allergens = item.get("allergens", [])
                if user_allergens and any(a in item_allergens for a in user_allergens):
                    continue
                
                # Add points for diet preference matches (use dietCategories or dietTags)
                item_diet_categories = item.get("dietCategories", []) or item.get("dietTags", [])
                if user_diet_prefs:
                    matches = sum(1 for d in user_diet_prefs if d in item_diet_categories)
                    if matches > 0:
                        preference_matches += 1
                    score += matches * 10
                
                total_matching_items += 1
                total_calories += item.get("calories", 0)
            else:
                # Simple string item - count as matching
                total_matching_items += 1
    
    # Bonus for being open
    if hall_data.get("isOpen"):
        score += 50
    
    # Bonus for having more matching items
    score += total_matching_items * 5
    
    # Calculate match rate (percentage)
    if total_items > 0:
        match_rate = min(100, max(60, int((total_matching_items / total_items) * 100) + (preference_matches * 5)))
    else:
        match_rate = 70
    
    return score, total_matching_items, total_calories, match_rate


def get_dining_halls_data(current_user=None, include_filtered=False):
    """Load dining hall data from database with reviews."""
    try:
        # Load dining halls from database
        db_halls = DiningHall.objects.all()
        
        response = []
        
        # Get user preferences
        user_allergens = []
        user_diet_prefs = []
        calorie_target = 2000
        
        if current_user and current_user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=current_user)
                user_allergens = profile.allergens or []
                user_diet_prefs = profile.dietPreferences or []
                calorie_target = profile.calorieTarget or 2000
            except UserProfile.DoesNotExist:
                pass

        for db_hall in db_halls:
            hall_id = db_hall.id
            hall_name = db_hall.hallName
            
            # Get reviews from database for this hall
            reviews_data = []
            user_review = None
            
            try:
                reviews = Review.objects.filter(diningHall=db_hall).select_related('user')
                for review in reviews:
                    review_dict = {
                        "id": review.id,
                        "userId": review.user.id,
                        "username": review.user.username,
                        "rating": review.rating,
                        "reviewText": review.reviewText,
                        "foodPreferences": review.foodPreferences,
                        "createdAt": review.createdAt.strftime("%Y-%m-%d %H:%M"),
                        "updatedAt": review.updatedAt.strftime("%Y-%m-%d %H:%M"),
                        "isOwner": current_user and current_user.is_authenticated and review.user.id == current_user.id,
                    }
                    reviews_data.append(review_dict)
                    
                    if current_user and current_user.is_authenticated and review.user.id == current_user.id:
                        user_review = review_dict
            except Exception as e:
                print(f"Error getting reviews for {hall_name}: {e}")
            
            # Calculate average rating
            avg_rating = sum(r["rating"] for r in reviews_data) / len(reviews_data) if reviews_data else 0
            
            # Get meals from database
            # IMPORTANT: Create a deep copy to avoid modifying the original data
            all_meals = copy.deepcopy(db_hall.meals) if db_hall.meals else {"breakfast": [], "lunch": [], "dinner": []}
            filtered_meals = filter_meals_for_user(all_meals, user_allergens, user_diet_prefs) if include_filtered else copy.deepcopy(all_meals)
            
            hall_data = {
                "id": hall_id,
                "hallName": hall_name,
                "hours": db_hall.hours,
                "mealHours": db_hall.mealHours or {},
                "isOpen": is_hall_open(db_hall.hours),
                "meals": all_meals,  # This is now a deep copy, safe from modification
                "filteredMeals": filtered_meals,
                "reviews": reviews_data,
                "avgRating": round(avg_rating, 1),
                "reviewCount": len(reviews_data),
                "userReview": user_review,
            }
            
            # Calculate recommendation score
            score, matching_items, total_calories, match_rate = calculate_hall_score(
                hall_data, user_allergens, user_diet_prefs
            )
            hall_data["score"] = score
            hall_data["matchingItems"] = matching_items
            hall_data["estimatedCalories"] = total_calories
            hall_data["matchRate"] = match_rate
            
            response.append(hall_data)

        return response
    except Exception as e:
        print(f"Error in get_dining_halls_data: {e}")
        import traceback
        traceback.print_exc()
        return []


def calculate_meal_specific_score(hall_data, meal_type, user_allergens=None, user_diet_prefs=None):
    """
    Calculate recommendation score for a specific meal type.
    Higher score = better match with user preferences.
    
    Scoring breakdown:
    - Safe items (no allergens): Base 10 points per item
    - Diet preference match: +15 points per matching preference
    - Hall is open: +50 points
    - Variety bonus: +2 points per safe item
    """
    score = 0
    safe_items = 0  # Items without user's allergens
    diet_matched_items = 0  # Items matching diet preferences
    total_items = 0
    
    meals = hall_data.get("meals", {})
    items = meals.get(meal_type, [])
    
    for item in items:
        total_items += 1
        if isinstance(item, dict):
            # Check allergens - skip items with user's allergens
            item_allergens = item.get("allergens", [])
            has_allergen = user_allergens and any(a in item_allergens for a in user_allergens)
            
            if has_allergen:
                continue  # Skip unsafe items
            
            # Item is safe
            safe_items += 1
            score += 10  # Base points for safe item
            
            # Check diet preference matches (support both dietCategories and dietTags)
            item_diet_categories = item.get("dietCategories", []) or item.get("dietTags", [])
            if user_diet_prefs and item_diet_categories:
                diet_matches = sum(1 for d in user_diet_prefs if d in item_diet_categories)
                if diet_matches > 0:
                    diet_matched_items += 1
                    score += diet_matches * 15  # Significant bonus for diet match
        else:
            # Simple string item - count as safe
            safe_items += 1
            score += 5
    
    # Bonus for being open
    if hall_data.get("isOpen"):
        score += 50
    
    # Variety bonus - reward halls with more safe options
    score += safe_items * 2
    
    # Calculate match rate percentage
    if total_items > 0:
        # Match rate based on safe items and diet matches
        safe_rate = (safe_items / total_items) * 100
        if user_diet_prefs:
            diet_rate = (diet_matched_items / safe_items * 100) if safe_items > 0 else 0
            match_rate = int(safe_rate * 0.7 + diet_rate * 0.3)  # Weighted average
        else:
            match_rate = int(safe_rate)
        match_rate = min(100, max(0, match_rate))
    else:
        match_rate = 0
    
    return score, safe_items, match_rate


def filter_meals_by_preferences(meals, user_allergens, user_diet_prefs):
    """
    Filter menu items based on user preferences.
    
    Rules:
    1. EXCLUDE items that contain ANY of the user's allergens (safety first)
    2. If user has diet preferences, ONLY SHOW items that match at least one preference
    3. If user has no diet preferences, show all safe items
    
    Args:
        meals: Dict with breakfast, lunch, dinner item lists
        user_allergens: List of allergen IDs to avoid
        user_diet_prefs: List of diet preference IDs
    
    Returns:
        Dict with filtered breakfast, lunch, dinner item lists
    """
    filtered = {
        'breakfast': [],
        'lunch': [],
        'dinner': []
    }
    
    for meal_type in ['breakfast', 'lunch', 'dinner']:
        items = meals.get(meal_type, [])
        
        for item in items:
            if isinstance(item, dict):
                # Check 1: Allergen safety (MUST PASS)
                item_allergens = item.get('allergens', [])
                has_allergen = user_allergens and any(a in item_allergens for a in user_allergens)
                
                if has_allergen:
                    continue  # Skip items with user's allergens
                
                # Check 2: Diet preference matching (if user has preferences)
                if user_diet_prefs:
                    # Support both dietCategories (from scraped data) and dietTags (from old format)
                    item_diet_categories = item.get('dietCategories', []) or item.get('dietTags', [])
                    matches_diet = any(d in item_diet_categories for d in user_diet_prefs)
                    
                    if matches_diet:
                        filtered[meal_type].append(item)
                else:
                    # No diet preferences - include all safe items
                    filtered[meal_type].append(item)
            else:
                # Simple string item - include if no allergens specified
                if not user_allergens:
                    filtered[meal_type].append(item)
    
    return filtered


@login_required
def recommendations_view(request):
    """Display personalized dining recommendations based on user preferences."""
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Don't redirect - just show a banner if preferences not set
    # This prevents the annoying redirect loop
    show_preferences_banner = not profile.surveyCompleted
    
    # Get meal type from URL parameter or auto-detect
    meal_param = request.GET.get('meal', None)
    weekend = is_weekend()
    
    # No breakfast on weekends
    if meal_param == 'breakfast' and weekend:
        current_meal = 'lunch'  # Default to lunch on weekend
    elif meal_param in ['breakfast', 'lunch', 'dinner']:
        current_meal = meal_param
    else:
        current_meal = get_current_meal_type()
    
    try:
        dining_halls = get_dining_halls_data(current_user=request.user, include_filtered=True)
        
        # Get user preferences
        user_allergens = profile.allergens or []
        user_diet_prefs = profile.dietPreferences or []
        
        # Get today's date to fetch menuByDate data
        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')
        
        # Get all dining halls from database to access menuByDate
        db_halls = DiningHall.objects.all()
        hall_menu_by_date = {}
        for db_hall in db_halls:
            if db_hall.menuByDate:
                try:
                    hall_dates = json.loads(db_hall.menuByDate)
                    # Find today's menu data
                    today_menu = next((d for d in hall_dates if d.get('date') == today_str), None)
                    if today_menu and today_menu.get('meals'):
                        hall_menu_by_date[db_hall.hallName] = today_menu.get('meals', {})
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Calculate meal-specific scores and filter meals for each hall
        for hall in dining_halls:
            hall_name = hall.get('hallName', '')
            
            # Use menuByDate data for today if available, otherwise fallback to meals field
            if hall_name in hall_menu_by_date:
                # Use today's menu from menuByDate (this has correct breakfast/lunch separation)
                original_meals = copy.deepcopy(hall_menu_by_date[hall_name])
                hall['meals'] = original_meals  # Update hall['meals'] with today's data
            else:
                # Fallback to meals field if menuByDate not available
                original_meals = hall.get('meals', {})
                if not original_meals:
                    original_meals = {"breakfast": [], "lunch": [], "dinner": []}
            
            # Calculate scores using the correct meal data
            meal_score, meal_items, meal_rate = calculate_meal_specific_score(
                hall, current_meal, user_allergens, user_diet_prefs
            )
            hall['mealScore'] = meal_score
            hall['matchingItems'] = meal_items
            hall['matchRate'] = meal_rate
            
            # Filter meals based on user preferences
            # Only show items that are safe (no allergens) AND match diet preferences
            # Filter meals separately for each meal type (breakfast, lunch, dinner)
            hall['filteredMeals'] = filter_meals_by_preferences(
                original_meals, user_allergens, user_diet_prefs
            )
            
            # Count filtered items for display
            hall['filteredCount'] = {
                'breakfast': len(hall['filteredMeals'].get('breakfast', [])),
                'lunch': len(hall['filteredMeals'].get('lunch', [])),
                'dinner': len(hall['filteredMeals'].get('dinner', []))
            }
        
        # Sort by match rate (percentage) first, then by score as tiebreaker
        # This ensures the displayed percentage matches the ranking order
        dining_halls.sort(key=lambda x: (x.get('matchRate', 0), x.get('mealScore', 0)), reverse=True)
        
        # Get top 2 recommendations for this meal
        top_halls = dining_halls[:2] if len(dining_halls) >= 2 else dining_halls
        
        context = {
            'dining_halls': dining_halls,
            'top_halls': top_halls,
            'current_meal': current_meal,
            'profile': profile,
            'calorie_target': profile.calorieTarget,
            'user_allergens': user_allergens,
            'user_diet_prefs': user_diet_prefs,
            'allergen_choices': ALLERGEN_CHOICES,
            'diet_choices': DIET_CHOICES,
            'is_weekend': weekend,
            'show_preferences_banner': show_preferences_banner,
            'error': None
        }
    except Exception as e:
        context = {
            'dining_halls': [],
            'top_halls': [],
            'current_meal': current_meal,
            'profile': profile,
            'calorie_target': 2000,
            'user_allergens': [],
            'user_diet_prefs': [],
            'allergen_choices': ALLERGEN_CHOICES,
            'diet_choices': DIET_CHOICES,
            'is_weekend': weekend,
            'show_preferences_banner': show_preferences_banner,
            'error': f"Error loading recommendations: {str(e)}"
        }
    
    return render(request, 'menus/recommendations.html', context)


@login_required
def menu_view(request):
    """Display dining halls with their menus and open/closed status."""
    weekend = is_weekend()
    
    try:
        dining_halls = get_dining_halls_data(current_user=request.user)
        
        # Get menuByDate for each dining hall
        all_halls = DiningHall.objects.all()
        menus_by_date = {}
        available_dates = []
        
        for hall in all_halls:
            # Parse menuByDate from TextField (stored as JSON string)
            if hall.menuByDate:
                try:
                    hall_dates = json.loads(hall.menuByDate)
                except (json.JSONDecodeError, TypeError):
                    hall_dates = []
            else:
                hall_dates = []
            menus_by_date[hall.hallName] = hall_dates
            
            # Collect available dates (use first hall's dates)
            if not available_dates and hall_dates:
                available_dates = [
                    {
                        'date': d.get('date'),
                        'dateDisplay': d.get('dateDisplay'),
                        'dayOfWeek': d.get('dayOfWeek'),
                        'isWeekend': d.get('isWeekend', False)
                    }
                    for d in hall_dates
                ]
        
        context = {
            'dining_halls': dining_halls,
            'menus_by_date': menus_by_date,
            'available_dates': available_dates,
            'food_preference_choices': Review.FOOD_PREFERENCE_CHOICES,
            'is_weekend': weekend,
            'error': None
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        context = {
            'dining_halls': [],
            'menus_by_date': {},
            'available_dates': [],
            'food_preference_choices': Review.FOOD_PREFERENCE_CHOICES,
            'is_weekend': weekend,
            'error': f"Error loading menu data: {str(e)}"
        }
    
    return render(request, 'menus/menu.html', context)


@login_required
def submit_review(request, hall_id):
    """Handle review creation or update via AJAX."""
    if request.method == "POST":
        try:
            hall = DiningHall.objects.get(pk=hall_id)
            rating = int(request.POST.get("rating", 5))
            reviewText = request.POST.get("reviewText", "")
            foodPreferences = request.POST.getlist("foodPreferences")
            
            # Try to get existing review, or create new one
            review, created = Review.objects.update_or_create(
                user=request.user,
                diningHall=hall,
                defaults={
                    'rating': rating,
                    'reviewText': reviewText,
                    'foodPreferences': foodPreferences,
                }
            )
            
            return JsonResponse({
                "success": True,
                "created": created,  # True if new, False if updated
                "review": {
                    "id": review.id,
                    "userId": review.user.id,
                    "username": review.user.username,
                    "rating": review.rating,
                    "reviewText": review.reviewText,
                    "foodPreferences": review.foodPreferences,
                    "createdAt": review.createdAt.strftime("%Y-%m-%d %H:%M"),
                    "updatedAt": review.updatedAt.strftime("%Y-%m-%d %H:%M"),
                    "isOwner": True,
                }
            })
        except DiningHall.DoesNotExist:
            return JsonResponse({"success": False, "error": "Dining hall not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)


@login_required
def delete_review(request, hall_id):
    """Handle review deletion via AJAX."""
    if request.method == "POST":
        try:
            hall = DiningHall.objects.get(pk=hall_id)
            
            # Only delete the current user's review
            review = Review.objects.get(user=request.user, diningHall=hall)
            review.delete()
            
            return JsonResponse({
                "success": True,
                "message": "Review deleted successfully"
            })
        except DiningHall.DoesNotExist:
            return JsonResponse({"success": False, "error": "Dining hall not found"}, status=404)
        except Review.DoesNotExist:
            return JsonResponse({"success": False, "error": "Review not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)


# ============== Meal History API ==============

@login_required
def get_meal_history(request):
    """
    Get user's meal history for the last 7 days.
    Returns a list of daily meal records with summary info.
    """
    try:
        # Get last 7 days
        today = datetime.now().date()
        start_date = today - timedelta(days=6)
        
        # Query meal history
        history = MealHistory.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today
        ).order_by('-date')
        
        # Create response with all 7 days (fill in missing days)
        history_dict = {h.date: h for h in history}
        result = []
        
        for i in range(7):
            date = today - timedelta(days=i)
            if date in history_dict:
                record = history_dict[date]
                result.append({
                    'id': record.id,
                    'date': record.date.strftime('%Y-%m-%d'),
                    'dateDisplay': record.date.strftime('%b %d'),
                    'dayOfWeek': record.date.strftime('%a'),
                    'meals': record.meals,
                    'totalCalories': record.totalCalories,
                    'mealCount': record.get_meal_count(),
                    'primaryHall': record.primaryHall,
                    'summary': record.get_summary(),
                    'hasData': True
                })
            else:
                # Empty day placeholder
                result.append({
                    'id': None,
                    'date': date.strftime('%Y-%m-%d'),
                    'dateDisplay': date.strftime('%b %d'),
                    'dayOfWeek': date.strftime('%a'),
                    'meals': [],
                    'totalCalories': 0,
                    'mealCount': 0,
                    'primaryHall': '',
                    'summary': {
                        'date': date.strftime('%Y-%m-%d'),
                        'dateDisplay': date.strftime('%b %d'),
                        'dayOfWeek': date.strftime('%a'),
                        'totalCalories': 0,
                        'mealCount': 0,
                        'primaryHall': '',
                        'breakfastCount': 0,
                        'lunchCount': 0,
                        'dinnerCount': 0,
                    },
                    'hasData': False
                })
        
        return JsonResponse({
            'success': True,
            'history': result
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def save_meal_history(request):
    """
    Save or update today's meal selection.
    Expects JSON body with meals array.
    """
    try:
        # Parse JSON body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            # Try form data
            data = {
                'meals': json.loads(request.POST.get('meals', '[]')),
                'date': request.POST.get('date', None)
            }
        
        meals = data.get('meals', [])
        date_str = data.get('date', None)
        
        # Use today if no date specified
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                date = datetime.now().date()
        else:
            date = datetime.now().date()
        
        # Calculate total calories
        total_calories = sum(m.get('calories', 0) for m in meals if isinstance(m, dict))
        
        # Determine primary dining hall (most visited)
        hall_counts = {}
        for meal in meals:
            if isinstance(meal, dict):
                hall = meal.get('diningHall', '')
                if hall:
                    hall_counts[hall] = hall_counts.get(hall, 0) + 1
        
        primary_hall = max(hall_counts, key=hall_counts.get) if hall_counts else ''
        
        # Create or update record
        record, created = MealHistory.objects.update_or_create(
            user=request.user,
            date=date,
            defaults={
                'meals': meals,
                'totalCalories': total_calories,
                'primaryHall': primary_hall
            }
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'record': {
                'id': record.id,
                'date': record.date.strftime('%Y-%m-%d'),
                'totalCalories': record.totalCalories,
                'mealCount': record.get_meal_count(),
                'primaryHall': record.primaryHall
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_meal_history_detail(request, date_str):
    """
    Get detailed meal history for a specific date.
    """
    try:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }, status=400)
        
        try:
            record = MealHistory.objects.get(user=request.user, date=date)
            return JsonResponse({
                'success': True,
                'record': {
                    'id': record.id,
                    'date': record.date.strftime('%Y-%m-%d'),
                    'dateDisplay': record.date.strftime('%b %d, %Y'),
                    'dayOfWeek': record.date.strftime('%A'),
                    'meals': record.meals,
                    'mealsByType': record.get_meals_by_type(),
                    'totalCalories': record.totalCalories,
                    'mealCount': record.get_meal_count(),
                    'primaryHall': record.primaryHall,
                    'createdAt': record.createdAt.strftime('%Y-%m-%d %H:%M'),
                    'updatedAt': record.updatedAt.strftime('%Y-%m-%d %H:%M'),
                }
            })
        except MealHistory.DoesNotExist:
            return JsonResponse({
                'success': True,
                'record': None,
                'message': 'No meal history for this date'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============== AI Assistant API ==============

def convert_db_menu_to_recommendation_format(dining_halls_data):
    """
    Convert database menu format to recommendation.py expected format.
    
    Database format: {
        "hallName": "Worcester",
        "meals": {
            "breakfast": [{"name": "...", "calories": 150, "allergens": [...], "dietTags": [...]}],
            "lunch": [...],
            "dinner": [...]
        }
    }
    
    Recommendation format: {
        "berkshire": [
            {
                "dish-name": "...",
                "meal-name": "breakfast",
                "allergens": [...],
                "diets": [...],
                "category-name": "..."
            }
        ]
    }
    """
    result = {}
    slug_mapping = {
        "Worcester": "worcester",
        "Hampshire": "hampshire",
        "Berkshire": "berkshire",
        "Franklin": "franklin"
    }
    
    for hall in dining_halls_data:
        hall_name = hall.get('hallName', '')
        slug = slug_mapping.get(hall_name, hall_name.lower())
        
        if slug not in result:
            result[slug] = []
        
        meals = hall.get('meals', {})
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            items = meals.get(meal_type, [])
            for item in items:
                if isinstance(item, dict):
                    converted_item = {
                        "dish-name": item.get('name', 'Unknown'),
                        "meal-name": meal_type,
                        "allergens": item.get('allergens', []),
                        "diets": item.get('dietTags', []),
                        "category-name": meal_type.capitalize(),
                        "calories": item.get('calories', 0)
                    }
                    result[slug].append(converted_item)
    
    return result


def get_user_preferences_for_recommendation(profile):
    """Convert UserProfile to recommendation.py expected preferences format."""
    return {
        "avoid_allergens": profile.allergens or [],
        "avoid_ingredients": [],  # Not stored in UserProfile currently
        "avoid_keywords": [],  # Not stored in UserProfile currently
        "diet": profile.dietPreferences or [],
        "likes": [],  # Not stored in UserProfile currently
        "dislikes": [],  # Not stored in UserProfile currently
        "goals": []  # Not stored in UserProfile currently
    }


@login_required
@require_http_methods(["POST"])
def ai_assistant_api(request):
    """
    AI Assistant API endpoint that uses recommendation.py to provide intelligent responses.
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'Message is required'
            }, status=400)
        
        # Get user profile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        # Get menu data from database
        dining_halls_data = get_dining_halls_data(current_user=request.user, include_filtered=False)
        
        # Convert to recommendation.py format
        menu_data = convert_db_menu_to_recommendation_format(dining_halls_data)
        
        # Get user preferences
        user_prefs = get_user_preferences_for_recommendation(profile)
        
        # Use recommendation.py to get recommendations (pass menu_data from database)
        recommendations = get_recommendations_for_all_dining(user_message, user_prefs, menu_data=menu_data)
        
        # Format response for display
        response_text = format_recommendations_response(recommendations, user_message)
        
        return JsonResponse({
            'success': True,
            'response': response_text,
            'recommendations': recommendations
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def format_recommendations_response(recommendations, user_message):
    """Format recommendations into a user-friendly text response."""
    hall_names = {
        'berkshire': 'Berkshire',
        'worcester': 'Worcester',
        'franklin': 'Franklin',
        'hampshire': 'Hampshire'
    }
    
    response_parts = []
    
    # Check if we have any recommendations
    has_recommendations = any(recommendations.get(slug, []) for slug in ['berkshire', 'worcester', 'franklin', 'hampshire'])
    
    if not has_recommendations:
        return "I couldn't find specific dishes matching your request, but I'd be happy to help you explore the dining options. Would you like me to suggest something based on your dietary preferences?"
    
    response_parts.append("Based on your request, here are my recommendations:")
    response_parts.append("")
    
    for slug in ['berkshire', 'worcester', 'franklin', 'hampshire']:
        dishes = recommendations.get(slug, [])
        if dishes:
            hall_name = hall_names.get(slug, slug.capitalize())
            response_parts.append(f"**{hall_name}:**")
            for dish in dishes[:3]:  # Limit to 3 dishes per hall
                response_parts.append(f"  • {dish}")
            response_parts.append("")
    
    return "\n".join(response_parts)
