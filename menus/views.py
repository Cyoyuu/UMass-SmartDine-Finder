from django.http import JsonResponse
from .models import DiningHall
from datetime import datetime

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
