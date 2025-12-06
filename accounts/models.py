from django.db import models
from django.contrib.auth.models import User


class UserFoodPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="food_pref")

    # Store structured preferences as JSON
    data = models.JSONField(default=dict)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} preferences"