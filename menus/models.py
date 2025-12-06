from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


class DiningHall(models.Model):
    hallName = models.CharField(max_length=100)
    hours = models.CharField(max_length=20)  # e.g. "07:00-20:00"
    mealHours = models.JSONField(default=dict, blank=True)
    meals = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.hallName


class Review(models.Model):
    """
    User review for a dining hall.
    - user: Foreign key to Django User model
    - diningHall: Foreign key to DiningHall model
    - reviewText: Review text content
    - rating: 1-5 star rating
    - foodPreferences: UMass Dining food category preferences (for recommendation system)
    - createdAt: Creation timestamp
    """
    
    # UMass Dining food category options
    FOOD_PREFERENCE_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('local', 'Local'),
        ('sustainable', 'Sustainable'),
        ('whole_grain', 'Whole Grain'),
        ('halal', 'Halal'),
        ('antibiotic_free', 'Antibiotic Free'),
        ('plant_based', 'Plant Based'),
    ]
    
    # Foreign key to Django User model
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    # Foreign key to DiningHall model
    diningHall = models.ForeignKey(
        DiningHall,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    # Review text content
    reviewText = models.TextField(max_length=1000)
    
    # Rating 1-5 stars
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Food preference categories (JSONField stores a list, e.g. ["vegetarian", "halal"])
    # Used for LLM-based recommendation system analysis
    foodPreferences = models.JSONField(
        default=list,
        blank=True,
        help_text="User's preferred food types, e.g. ['vegetarian', 'halal']"
    )
    
    # Creation timestamp
    createdAt = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-createdAt']  # Default ordering by creation time (newest first)
    
    def __str__(self):
        return f"{self.user.username} - {self.diningHall.hallName} - {self.rating}★"
    
    def get_preference_display_list(self):
        """Get display names for user's food preferences."""
        preference_map = dict(self.FOOD_PREFERENCE_CHOICES)
        return [preference_map.get(pref, pref) for pref in self.foodPreferences]
