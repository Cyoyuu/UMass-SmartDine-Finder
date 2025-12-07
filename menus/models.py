from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


# Allergen choices for user preferences and menu items
# Synced with scraped menu data from UMass Dining
ALLERGEN_CHOICES = [
    ('dairy', 'Dairy'),
    ('eggs', 'Eggs'),
    ('fish', 'Fish'),
    ('gluten', 'Gluten'),
    ('peanuts', 'Peanuts'),
    ('soy', 'Soy'),
    ('sesame', 'Sesame'),
    ('corn', 'Corn'),
]

# Diet preference choices
# Synced with scraped menu data diet categories from UMass Dining
DIET_CHOICES = [
    ('vegetarian', 'Vegetarian'),
    ('plant_based', 'Plant Based'),
    ('halal', 'Halal'),
    ('local', 'Local'),
    ('sustainable', 'Sustainable'),
    ('whole_grain', 'Whole Grain'),
    ('antibiotic_free', 'Antibiotic Free'),
]


class UserProfile(models.Model):
    """
    User profile storing dietary preferences for recommendations.
    - allergens: List of allergens to avoid
    - calorieTarget: Daily calorie target (default 2000)
    - dietPreferences: Diet preferences (vegetarian, vegan, etc.)
    - surveyCompleted: Whether user has completed the survey
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Allergens to avoid (JSONField stores a list, e.g. ["milk", "eggs"])
    allergens = models.JSONField(
        default=list,
        blank=True,
        help_text="Allergens to avoid, e.g. ['milk', 'eggs']"
    )
    
    # Daily calorie target (default 2000)
    calorieTarget = models.IntegerField(
        default=2000,
        validators=[MinValueValidator(500), MaxValueValidator(5000)],
        help_text="Daily calorie target"
    )
    
    # Diet preferences (JSONField stores a list)
    dietPreferences = models.JSONField(
        default=list,
        blank=True,
        help_text="Diet preferences, e.g. ['vegetarian', 'halal']"
    )
    
    # Whether survey has been completed
    surveyCompleted = models.BooleanField(default=False)
    
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @classmethod
    def get_allergen_choices(cls):
        return ALLERGEN_CHOICES
    
    @classmethod
    def get_diet_choices(cls):
        return DIET_CHOICES


# Auto-create UserProfile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class MenuItem(models.Model):
    """
    Individual menu item with nutrition information.
    - name: Item name
    - calories: Calorie count
    - allergens: List of allergens present
    - dietTags: Diet tags (vegetarian, vegan, etc.)
    """
    name = models.CharField(max_length=200)
    calories = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    allergens = models.JSONField(
        default=list,
        blank=True,
        help_text="Allergens present, e.g. ['milk', 'gluten']"
    )
    dietTags = models.JSONField(
        default=list,
        blank=True,
        help_text="Diet tags, e.g. ['vegetarian', 'halal']"
    )
    
    def __str__(self):
        return f"{self.name} ({self.calories} cal)"
    
    def is_safe_for_user(self, user_allergens):
        """Check if item is safe for user with given allergens."""
        if not user_allergens:
            return True
        return not any(a in self.allergens for a in user_allergens)
    
    def matches_diet(self, user_diet_prefs):
        """Check if item matches user's diet preferences."""
        if not user_diet_prefs:
            return True
        return any(d in self.dietTags for d in user_diet_prefs)


class DiningHall(models.Model):
    hallName = models.CharField(max_length=100)
    hours = models.CharField(max_length=20)  # e.g. "07:00-20:00"
    mealHours = models.JSONField(default=dict, blank=True)
    # Updated meals structure with nutrition info
    # Format: {"breakfast": [{"name": "Oatmeal", "calories": 150, "allergens": [], "dietTags": ["vegetarian"]}], ...}
    meals = models.JSONField(default=dict, blank=True)
    # Menu data organized by date for date-specific views
    # Format: [{"date": "2025-12-06", "dateDisplay": "Dec 6", "dayOfWeek": "Saturday", "isWeekend": true, "meals": {...}}, ...]
    # Note: Database stores this as TextField, not JSONField
    menuByDate = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.hallName
    
    def get_filtered_meals(self, user_allergens=None, user_diet_prefs=None):
        """Get meals filtered by user preferences."""
        filtered = {"breakfast": [], "lunch": [], "dinner": []}
        
        for meal_type in ["breakfast", "lunch", "dinner"]:
            items = self.meals.get(meal_type, [])
            for item in items:
                # Handle both old format (string) and new format (dict)
                if isinstance(item, str):
                    filtered[meal_type].append({
                        "name": item,
                        "calories": 0,
                        "allergens": [],
                        "dietTags": []
                    })
                else:
                    # Check allergens
                    item_allergens = item.get("allergens", [])
                    if user_allergens and any(a in item_allergens for a in user_allergens):
                        continue  # Skip items with user's allergens
                    
                    # Check diet preferences (if user has any, item must match at least one)
                    item_diet_tags = item.get("dietTags", [])
                    if user_diet_prefs and not any(d in item_diet_tags for d in user_diet_prefs):
                        continue
                    
                    filtered[meal_type].append(item)
        
        return filtered
    
    def calculate_meal_calories(self, meal_items):
        """Calculate total calories for a list of meal items."""
        total = 0
        for item in meal_items:
            if isinstance(item, dict):
                total += item.get("calories", 0)
        return total


class MealHistory(models.Model):
    """
    Daily meal history for a user.
    Stores user's meal selections for each day, enabling history tracking
    and statistics on the preferences page.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='meal_history'
    )
    
    date = models.DateField(
        help_text="Date of the meal selection"
    )
    
    # Meal selections stored as a list of items with details
    # Format: [{"name": "Oatmeal", "calories": 150, "diningHall": "Hampshire", "mealType": "breakfast"}, ...]
    meals = models.JSONField(
        default=list,
        blank=True,
        help_text="List of selected meal items for the day"
    )
    
    # Total calories for the day
    totalCalories = models.IntegerField(
        default=0,
        help_text="Total calories consumed for the day"
    )
    
    # Primary dining hall visited that day
    primaryHall = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Most visited dining hall that day"
    )
    
    # Timestamps
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        # Each user can only have one record per day
        unique_together = ['user', 'date']
        verbose_name_plural = 'Meal histories'
    
    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.totalCalories} cal)"
    
    def get_meal_count(self):
        """Get the number of meals selected."""
        return len(self.meals) if self.meals else 0
    
    def get_meals_by_type(self):
        """Get meals grouped by meal type."""
        grouped = {'breakfast': [], 'lunch': [], 'dinner': [], 'snack': []}
        for meal in (self.meals or []):
            meal_type = meal.get('mealType', 'snack')
            if meal_type in grouped:
                grouped[meal_type].append(meal)
            else:
                grouped['snack'].append(meal)
        return grouped
    
    def get_summary(self):
        """Get a summary of the day's meals."""
        meal_count = self.get_meal_count()
        by_type = self.get_meals_by_type()
        return {
            'date': self.date.strftime('%Y-%m-%d'),
            'dateDisplay': self.date.strftime('%b %d'),
            'dayOfWeek': self.date.strftime('%a'),
            'totalCalories': self.totalCalories,
            'mealCount': meal_count,
            'primaryHall': self.primaryHall,
            'breakfastCount': len(by_type['breakfast']),
            'lunchCount': len(by_type['lunch']),
            'dinnerCount': len(by_type['dinner']),
        }


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
    
    # Timestamps
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-createdAt']  # Default ordering by creation time (newest first)
        # Each user can only have one review per dining hall
        unique_together = ['user', 'diningHall']
    
    def __str__(self):
        return f"{self.user.username} - {self.diningHall.hallName} - {self.rating}★"
    
    def get_preference_display_list(self):
        """Get display names for user's food preferences."""
        preference_map = dict(self.FOOD_PREFERENCE_CHOICES)
        return [preference_map.get(pref, pref) for pref in self.foodPreferences]
