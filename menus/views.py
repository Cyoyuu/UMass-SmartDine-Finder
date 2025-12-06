from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import datetime
from .models import DiningHall, Review


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


def get_dining_halls_data():
    """Load dining hall data from database with reviews."""
    try:
        halls = DiningHall.objects.all()
        response = []

        for hall in halls:
            # Get reviews for this dining hall
            reviews = Review.objects.filter(diningHall=hall).select_related('user')
            reviews_data = []
            for review in reviews:
                reviews_data.append({
                    "id": review.id,
                    "username": review.user.username,
                    "rating": review.rating,
                    "reviewText": review.reviewText,
                    "foodPreferences": review.foodPreferences,
                    "createdAt": review.createdAt.strftime("%Y-%m-%d %H:%M"),
                })
            
            # Calculate average rating
            avg_rating = sum(r["rating"] for r in reviews_data) / len(reviews_data) if reviews_data else 0
            
            response.append({
                "id": hall.id,
                "hallName": hall.hallName,
                "hours": hall.hours,
                "mealHours": hall.mealHours,
                "isOpen": is_hall_open(hall.hours),
                "meals": hall.meals or {"breakfast": [], "lunch": [], "dinner": []},
                "reviews": reviews_data,
                "avgRating": round(avg_rating, 1),
                "reviewCount": len(reviews_data),
            })

        return response
    except Exception:
        return []


@login_required
def menu_view(request):
    """Display dining halls with their menus and open/closed status."""
    try:
        dining_halls = get_dining_halls_data()
        
        context = {
            'dining_halls': dining_halls,
            'food_preference_choices': Review.FOOD_PREFERENCE_CHOICES,
            'error': None
        }
    except Exception as e:
        context = {
            'dining_halls': [],
            'food_preference_choices': Review.FOOD_PREFERENCE_CHOICES,
            'error': f"Error loading menu data: {str(e)}"
        }
    
    return render(request, 'menus/menu.html', context)


@login_required
def api_menus_view(request):
    """API endpoint that returns dining hall data as JSON."""
    try:
        dining_halls = get_dining_halls_data()
        return JsonResponse(dining_halls, safe=False)
    except Exception as e:
        return JsonResponse({'error': f"Error loading menu data: {str(e)}"}, status=500)


@login_required
def submit_review(request, hall_id):
    """Handle review submission via AJAX."""
    if request.method == "POST":
        try:
            hall = DiningHall.objects.get(pk=hall_id)
            rating = int(request.POST.get("rating", 5))
            reviewText = request.POST.get("reviewText", "")
            foodPreferences = request.POST.getlist("foodPreferences")
            
            review = Review.objects.create(
                user=request.user,
                diningHall=hall,
                rating=rating,
                reviewText=reviewText,
                foodPreferences=foodPreferences
            )
            
            return JsonResponse({
                "success": True,
                "review": {
                    "id": review.id,
                    "username": review.user.username,
                    "rating": review.rating,
                    "reviewText": review.reviewText,
                    "foodPreferences": review.foodPreferences,
                    "createdAt": review.createdAt.strftime("%Y-%m-%d %H:%M"),
                }
            })
        except DiningHall.DoesNotExist:
            return JsonResponse({"success": False, "error": "Dining hall not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)
