from django.http import JsonResponse
from .models import DiningHall
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import DiningHall, Review

print("### menus_view loaded ###")

def is_open_now(hours_str):
    """Check if current time is within open hours (HH:MM-HH:MM)."""
    try:
        open_time_str, close_time_str = hours_str.split('-')
        now = datetime.now().time()
        open_time = datetime.strptime(open_time_str, "%H:%M").time()
        close_time = datetime.strptime(close_time_str, "%H:%M").time()
        return open_time <= now <= close_time
    except Exception:
        return False

def menus_view(request):
    halls = DiningHall.objects.all()
    response = []

    for hall in halls:
        response.append({
            "hallName": hall.name,
            "hours": hall.hours,
            "isOpen": is_open_now(hall.hours),
            "meals": hall.meals or {"breakfast": [], "lunch": [], "dinner": []}
        })

    return JsonResponse(response, safe=False)

@login_required
def writeReview(request, hall_id):
    hall = get_object_or_404(DiningHall, pk=hall_id)

    if request.method == "POST":
        rating = request.POST.get("rating")
        reviewText = request.POST.get("reviewText")

        Review.objects.create(
            username=request.user.username,
            diningHall=hall,
            rating=rating,
            reviewText=reviewText,
            likes=0
        )

        return redirect("dining_hall_detail", hall_id=hall.id)

    context = {
        "username": request.user.username,
        "diningHall": hall,
    }
    return render(request, "write_review.html", context)