from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import datetime, date, timedelta
import json

from .models import (
    UserProfile, MenuItem, DiningHall, Review, MealHistory,
    ALLERGEN_CHOICES, DIET_CHOICES
)


class UserProfileModelTest(TestCase):
    """Test cases for UserProfile model."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_profile_auto_created(self):
        """Test that UserProfile is automatically created when User is created."""
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.user, self.user)
    
    def test_user_profile_defaults(self):
        """Test default values for UserProfile."""
        profile = self.user.profile
        self.assertEqual(profile.allergens, [])
        self.assertEqual(profile.calorieTarget, 2000)
        self.assertEqual(profile.dietPreferences, [])
        self.assertFalse(profile.surveyCompleted)
    
    def test_user_profile_str(self):
        """Test UserProfile string representation."""
        profile = self.user.profile
        self.assertEqual(str(profile), "testuser's Profile")
    
    def test_calorie_target_validators(self):
        """Test calorie target validators."""
        profile = self.user.profile
        # Test minimum value
        profile.calorieTarget = 499
        with self.assertRaises(ValidationError):
            profile.full_clean()
        
        # Test maximum value
        profile.calorieTarget = 5001
        with self.assertRaises(ValidationError):
            profile.full_clean()
        
        # Test valid values
        profile.calorieTarget = 500
        profile.full_clean()
        profile.calorieTarget = 5000
        profile.full_clean()
    
    def test_allergens_storage(self):
        """Test storing allergens as JSON."""
        profile = self.user.profile
        profile.allergens = ['dairy', 'gluten']
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.allergens, ['dairy', 'gluten'])
    
    def test_diet_preferences_storage(self):
        """Test storing diet preferences as JSON."""
        profile = self.user.profile
        profile.dietPreferences = ['vegetarian', 'halal']
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.dietPreferences, ['vegetarian', 'halal'])
    
    def test_get_allergen_choices(self):
        """Test get_allergen_choices class method."""
        choices = UserProfile.get_allergen_choices()
        self.assertEqual(choices, ALLERGEN_CHOICES)
    
    def test_get_diet_choices(self):
        """Test get_diet_choices class method."""
        choices = UserProfile.get_diet_choices()
        self.assertEqual(choices, DIET_CHOICES)


class MenuItemModelTest(TestCase):
    """Test cases for MenuItem model."""
    
    def setUp(self):
        """Set up test menu item."""
        self.menu_item = MenuItem.objects.create(
            name='Grilled Chicken',
            calories=250,
            allergens=['eggs'],
            dietTags=['halal', 'antibiotic_free']
        )
    
    def test_menu_item_creation(self):
        """Test creating a menu item."""
        self.assertEqual(self.menu_item.name, 'Grilled Chicken')
        self.assertEqual(self.menu_item.calories, 250)
        self.assertEqual(self.menu_item.allergens, ['eggs'])
        self.assertEqual(self.menu_item.dietTags, ['halal', 'antibiotic_free'])
    
    def test_menu_item_str(self):
        """Test MenuItem string representation."""
        self.assertEqual(str(self.menu_item), 'Grilled Chicken (250 cal)')
    
    def test_is_safe_for_user(self):
        """Test is_safe_for_user method."""
        # User has no allergens - should be safe
        self.assertTrue(self.menu_item.is_safe_for_user([]))
        
        # User has different allergens - should be safe
        self.assertTrue(self.menu_item.is_safe_for_user(['dairy', 'peanuts']))
        
        # User has matching allergen - should not be safe
        self.assertFalse(self.menu_item.is_safe_for_user(['eggs']))
        
        # User has multiple allergens, one matches - should not be safe
        self.assertFalse(self.menu_item.is_safe_for_user(['dairy', 'eggs']))
    
    def test_matches_diet(self):
        """Test matches_diet method."""
        # No diet preferences - should match
        self.assertTrue(self.menu_item.matches_diet([]))
        
        # Matching diet preference - should match
        self.assertTrue(self.menu_item.matches_diet(['halal']))
        self.assertTrue(self.menu_item.matches_diet(['antibiotic_free']))
        
        # Non-matching diet preference - should not match
        self.assertFalse(self.menu_item.matches_diet(['vegetarian']))
        
        # Multiple preferences, one matches - should match
        self.assertTrue(self.menu_item.matches_diet(['vegetarian', 'halal']))
    
    def test_calories_validator(self):
        """Test calories validator (non-negative)."""
        item = MenuItem(name='Test', calories=-10)
        with self.assertRaises(ValidationError):
            item.full_clean()
        
        item.calories = 0
        item.full_clean()  # Should not raise


class DiningHallModelTest(TestCase):
    """Test cases for DiningHall model."""
    
    def setUp(self):
        """Set up test dining hall."""
        self.hall = DiningHall.objects.create(
            hallName='Berkshire',
            hours='07:00-20:00',
            mealHours={
                'breakfast': '07:00-10:30',
                'lunch': '11:00-15:00',
                'dinner': '17:00-20:00'
            },
            meals={
                'breakfast': [
                    {'name': 'Oatmeal', 'calories': 150, 'allergens': [], 'dietTags': ['vegetarian']}
                ],
                'lunch': [
                    {'name': 'Grilled Chicken', 'calories': 250, 'allergens': ['eggs'], 'dietTags': ['halal']},
                    {'name': 'Salad', 'calories': 100, 'allergens': [], 'dietTags': ['vegetarian']}
                ],
                'dinner': []
            }
        )
    
    def test_dining_hall_creation(self):
        """Test creating a dining hall."""
        self.assertEqual(self.hall.hallName, 'Berkshire')
        self.assertEqual(self.hall.hours, '07:00-20:00')
        self.assertIsInstance(self.hall.meals, dict)
        self.assertIn('breakfast', self.hall.meals)
    
    def test_dining_hall_str(self):
        """Test DiningHall string representation."""
        self.assertEqual(str(self.hall), 'Berkshire')
    
    def test_get_filtered_meals_no_preferences(self):
        """Test filtering meals with no user preferences."""
        filtered = self.hall.get_filtered_meals()
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(len(filtered['lunch']), 2)
    
    def test_get_filtered_meals_with_allergens(self):
        """Test filtering meals with allergen restrictions."""
        filtered = self.hall.get_filtered_meals(user_allergens=['eggs'])
        # Should exclude Grilled Chicken
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(len(filtered['lunch']), 1)
        self.assertEqual(filtered['lunch'][0]['name'], 'Salad')
    
    def test_get_filtered_meals_with_diet_preferences(self):
        """Test filtering meals with diet preferences."""
        filtered = self.hall.get_filtered_meals(user_diet_prefs=['vegetarian'])
        # Should only include items with vegetarian tag
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(len(filtered['lunch']), 1)
        self.assertEqual(filtered['lunch'][0]['name'], 'Salad')
    
    def test_get_filtered_meals_combined(self):
        """Test filtering meals with both allergens and diet preferences."""
        filtered = self.hall.get_filtered_meals(
            user_allergens=['eggs'],
            user_diet_prefs=['vegetarian']
        )
        # Should exclude Grilled Chicken (has eggs), keep only vegetarian items
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(len(filtered['lunch']), 1)
    
    def test_calculate_meal_calories(self):
        """Test calculating total calories for meal items."""
        items = [
            {'name': 'Item1', 'calories': 100},
            {'name': 'Item2', 'calories': 200},
            {'name': 'Item3', 'calories': 150}
        ]
        total = self.hall.calculate_meal_calories(items)
        self.assertEqual(total, 450)
    
    def test_calculate_meal_calories_with_strings(self):
        """Test calculating calories with string items (old format)."""
        items = [
            'Item1',
            {'name': 'Item2', 'calories': 200}
        ]
        total = self.hall.calculate_meal_calories(items)
        self.assertEqual(total, 200)


class ReviewModelTest(TestCase):
    """Test cases for Review model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.hall = DiningHall.objects.create(
            hallName='Berkshire',
            hours='07:00-20:00'
        )
    
    def test_review_creation(self):
        """Test creating a review."""
        review = Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='Great food!',
            rating=5,
            foodPreferences=['vegetarian', 'halal']
        )
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.diningHall, self.hall)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.foodPreferences, ['vegetarian', 'halal'])
    
    def test_review_str(self):
        """Test Review string representation."""
        review = Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='Great!',
            rating=4
        )
        self.assertEqual(str(review), 'testuser - Berkshire - 4★')
    
    def test_review_rating_validators(self):
        """Test review rating validators."""
        # Test minimum value
        review = Review(
            user=self.user,
            diningHall=self.hall,
            reviewText='Test',
            rating=0
        )
        with self.assertRaises(ValidationError):
            review.full_clean()
        
        # Test maximum value
        review.rating = 6
        with self.assertRaises(ValidationError):
            review.full_clean()
        
        # Test valid values
        review.rating = 1
        review.full_clean()
        review.rating = 5
        review.full_clean()
    
    def test_review_unique_together(self):
        """Test that a user can only have one review per dining hall."""
        Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='First review',
            rating=5
        )
        
        # Should raise IntegrityError when trying to create duplicate
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                user=self.user,
                diningHall=self.hall,
                reviewText='Second review',
                rating=4
            )
    
    def test_review_update(self):
        """Test updating an existing review."""
        review = Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='First review',
            rating=5
        )
        
        # Update using update_or_create
        Review.objects.update_or_create(
            user=self.user,
            diningHall=self.hall,
            defaults={
                'reviewText': 'Updated review',
                'rating': 4
            }
        )
        
        review.refresh_from_db()
        self.assertEqual(review.reviewText, 'Updated review')
        self.assertEqual(review.rating, 4)
    
    def test_get_preference_display_list(self):
        """Test get_preference_display_list method."""
        review = Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='Test',
            rating=5,
            foodPreferences=['vegetarian', 'halal']
        )
        display_list = review.get_preference_display_list()
        self.assertIn('Vegetarian', display_list)
        self.assertIn('Halal', display_list)


class MealHistoryModelTest(TestCase):
    """Test cases for MealHistory model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.today = date.today()
    
    def test_meal_history_creation(self):
        """Test creating a meal history record."""
        meals = [
            {
                'name': 'Oatmeal',
                'calories': 150,
                'diningHall': 'Berkshire',
                'mealType': 'breakfast'
            },
            {
                'name': 'Grilled Chicken',
                'calories': 250,
                'diningHall': 'Berkshire',
                'mealType': 'lunch'
            }
        ]
        
        history = MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=meals,
            totalCalories=400,
            primaryHall='Berkshire'
        )
        
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.date, self.today)
        self.assertEqual(history.totalCalories, 400)
        self.assertEqual(history.primaryHall, 'Berkshire')
    
    def test_meal_history_str(self):
        """Test MealHistory string representation."""
        history = MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=[],
            totalCalories=500
        )
        self.assertIn('testuser', str(history))
        self.assertIn(str(self.today), str(history))
        self.assertIn('500 cal', str(history))
    
    def test_meal_history_unique_together(self):
        """Test that a user can only have one record per day."""
        MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=[],
            totalCalories=500
        )
        
        # Should raise IntegrityError when trying to create duplicate
        with self.assertRaises(IntegrityError):
            MealHistory.objects.create(
                user=self.user,
                date=self.today,
                meals=[],
                totalCalories=600
            )
    
    def test_get_meal_count(self):
        """Test get_meal_count method."""
        meals = [
            {'name': 'Item1', 'calories': 100},
            {'name': 'Item2', 'calories': 200}
        ]
        history = MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=meals,
            totalCalories=300
        )
        self.assertEqual(history.get_meal_count(), 2)
    
    def test_get_meals_by_type(self):
        """Test get_meals_by_type method."""
        meals = [
            {'name': 'Breakfast Item', 'mealType': 'breakfast'},
            {'name': 'Lunch Item', 'mealType': 'lunch'},
            {'name': 'Dinner Item', 'mealType': 'dinner'},
            {'name': 'Unknown Item'}  # Should go to snack
        ]
        history = MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=meals,
            totalCalories=400
        )
        
        by_type = history.get_meals_by_type()
        self.assertEqual(len(by_type['breakfast']), 1)
        self.assertEqual(len(by_type['lunch']), 1)
        self.assertEqual(len(by_type['dinner']), 1)
        self.assertEqual(len(by_type['snack']), 1)
    
    def test_get_summary(self):
        """Test get_summary method."""
        meals = [
            {'name': 'Breakfast Item', 'mealType': 'breakfast'},
            {'name': 'Lunch Item', 'mealType': 'lunch'},
        ]
        history = MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=meals,
            totalCalories=350,
            primaryHall='Berkshire'
        )
        
        summary = history.get_summary()
        self.assertEqual(summary['totalCalories'], 350)
        self.assertEqual(summary['mealCount'], 2)
        self.assertEqual(summary['primaryHall'], 'Berkshire')
        self.assertEqual(summary['breakfastCount'], 1)
        self.assertEqual(summary['lunchCount'], 1)
        self.assertEqual(summary['dinnerCount'], 0)
        self.assertIn('date', summary)
        self.assertIn('dateDisplay', summary)
        self.assertIn('dayOfWeek', summary)
    
    def test_meal_history_ordering(self):
        """Test that meal history is ordered by date descending."""
        yesterday = self.today - timedelta(days=1)
        day_before = self.today - timedelta(days=2)
        
        history1 = MealHistory.objects.create(
            user=self.user,
            date=day_before,
            meals=[],
            totalCalories=100
        )
        history2 = MealHistory.objects.create(
            user=self.user,
            date=yesterday,
            meals=[],
            totalCalories=200
        )
        history3 = MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=[],
            totalCalories=300
        )
        
        histories = list(MealHistory.objects.filter(user=self.user))
        self.assertEqual(histories[0].date, self.today)
        self.assertEqual(histories[1].date, yesterday)
        self.assertEqual(histories[2].date, day_before)


# ============== View Tests ==============

from django.test import Client
from django.urls import reverse
from unittest.mock import patch, MagicMock


class MenuViewTest(TestCase):
    """Test cases for menu view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.hall = DiningHall.objects.create(
            hallName='Berkshire',
            hours='07:00-20:00',
            meals={
                'breakfast': [{'name': 'Oatmeal', 'calories': 150}],
                'lunch': [{'name': 'Sandwich', 'calories': 300}],
                'dinner': []
            }
        )
    
    def test_menu_view_unauthenticated(self):
        """Test accessing menu view when not authenticated."""
        response = self.client.get(reverse('menu'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_menu_view_authenticated(self):
        """Test accessing menu view when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('menu'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menus/menu.html')
        self.assertIn('dining_halls', response.context)
    
    def test_menu_view_with_data(self):
        """Test menu view with dining hall data."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('menu'))
        
        self.assertEqual(response.status_code, 200)
        dining_halls = response.context['dining_halls']
        self.assertEqual(len(dining_halls), 1)
        self.assertEqual(dining_halls[0]['hallName'], 'Berkshire')


class RecommendationsViewTest(TestCase):
    """Test cases for recommendations view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.hall = DiningHall.objects.create(
            hallName='Berkshire',
            hours='07:00-20:00',
            meals={
                'breakfast': [
                    {'name': 'Oatmeal', 'calories': 150, 'allergens': [], 'dietTags': ['vegetarian']}
                ],
                'lunch': [
                    {'name': 'Grilled Chicken', 'calories': 250, 'allergens': ['eggs'], 'dietTags': ['halal']},
                    {'name': 'Salad', 'calories': 100, 'allergens': [], 'dietTags': ['vegetarian']}
                ],
                'dinner': []
            }
        )
    
    def test_recommendations_view_unauthenticated(self):
        """Test accessing recommendations view when not authenticated."""
        response = self.client.get(reverse('recommendations'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_recommendations_view_authenticated(self):
        """Test accessing recommendations view when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menus/recommendations.html')
        self.assertIn('dining_halls', response.context)
        self.assertIn('current_meal', response.context)
    
    def test_recommendations_view_with_preferences(self):
        """Test recommendations view with user preferences."""
        self.client.login(username='testuser', password='testpass123')
        
        # Set user preferences
        profile = self.user.profile
        profile.allergens = ['eggs']
        profile.dietPreferences = ['vegetarian']
        profile.surveyCompleted = True
        profile.save()
        
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        
        # Should filter out items with eggs
        dining_halls = response.context['dining_halls']
        self.assertEqual(len(dining_halls), 1)
        
        # Check filtered meals exclude items with allergens
        filtered_meals = dining_halls[0].get('filteredMeals', {})
        # Should not have Grilled Chicken (contains eggs)
        lunch_items = filtered_meals.get('lunch', [])
        item_names = [item.get('name') for item in lunch_items if isinstance(item, dict)]
        self.assertNotIn('Grilled Chicken', item_names)
    
    def test_recommendations_view_meal_parameter(self):
        """Test recommendations view with meal parameter."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('recommendations') + '?meal=lunch')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_meal'], 'lunch')


class ReviewViewTest(TestCase):
    """Test cases for review views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.hall = DiningHall.objects.create(
            hallName='Berkshire',
            hours='07:00-20:00'
        )
    
    def test_submit_review_unauthenticated(self):
        """Test submitting review when not authenticated."""
        response = self.client.post(reverse('submit_review', args=[self.hall.id]))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_submit_review_authenticated(self):
        """Test submitting a review when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('submit_review', args=[self.hall.id]),
            {
                'rating': '5',
                'reviewText': 'Great food!',
                'foodPreferences': ['vegetarian', 'halal']
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['created'])
        
        # Check review was created
        review = Review.objects.get(user=self.user, diningHall=self.hall)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.reviewText, 'Great food!')
        self.assertEqual(review.foodPreferences, ['vegetarian', 'halal'])
    
    def test_submit_review_update(self):
        """Test updating an existing review."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create initial review
        Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='Initial review',
            rating=3
        )
        
        # Update review
        response = self.client.post(
            reverse('submit_review', args=[self.hall.id]),
            {
                'rating': '5',
                'reviewText': 'Updated review',
                'foodPreferences': ['vegetarian']
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['created'])  # Not created, updated
        
        # Check review was updated
        review = Review.objects.get(user=self.user, diningHall=self.hall)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.reviewText, 'Updated review')
    
    def test_submit_review_invalid_hall(self):
        """Test submitting review for non-existent hall."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('submit_review', args=[9999]),
            {
                'rating': '5',
                'reviewText': 'Test'
            }
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
    
    def test_delete_review_unauthenticated(self):
        """Test deleting review when not authenticated."""
        response = self.client.post(reverse('delete_review', args=[self.hall.id]))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_delete_review_authenticated(self):
        """Test deleting a review when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create review
        Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='Test review',
            rating=5
        )
        
        # Delete review
        response = self.client.post(reverse('delete_review', args=[self.hall.id]))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check review was deleted
        self.assertFalse(Review.objects.filter(user=self.user, diningHall=self.hall).exists())
    
    def test_delete_review_nonexistent(self):
        """Test deleting a non-existent review."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('delete_review', args=[self.hall.id]))
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class MealHistoryViewTest(TestCase):
    """Test cases for meal history views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.today = date.today()
    
    def test_get_meal_history_unauthenticated(self):
        """Test getting meal history when not authenticated."""
        response = self.client.get(reverse('meal_history'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_get_meal_history_authenticated(self):
        """Test getting meal history when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create some meal history
        MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=[
                {'name': 'Breakfast', 'calories': 300, 'mealType': 'breakfast'}
            ],
            totalCalories=300
        )
        
        response = self.client.get(reverse('meal_history'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['history']), 7)  # Last 7 days
        
        # Check today's data is present
        today_data = next((d for d in data['history'] if d['hasData']), None)
        self.assertIsNotNone(today_data)
        self.assertEqual(today_data['totalCalories'], 300)
    
    def test_save_meal_history_unauthenticated(self):
        """Test saving meal history when not authenticated."""
        response = self.client.post(reverse('save_meal_history'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_save_meal_history_authenticated(self):
        """Test saving meal history when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        
        meals = [
            {
                'name': 'Oatmeal',
                'calories': 150,
                'diningHall': 'Berkshire',
                'mealType': 'breakfast'
            },
            {
                'name': 'Sandwich',
                'calories': 300,
                'diningHall': 'Berkshire',
                'mealType': 'lunch'
            }
        ]
        
        response = self.client.post(
            reverse('save_meal_history'),
            json.dumps({'meals': meals}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['created'])
        
        # Check meal history was created
        history = MealHistory.objects.get(user=self.user, date=self.today)
        self.assertEqual(history.totalCalories, 450)
        self.assertEqual(history.primaryHall, 'Berkshire')
        self.assertEqual(len(history.meals), 2)
    
    def test_save_meal_history_update(self):
        """Test updating existing meal history."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create initial history
        MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=[],
            totalCalories=0
        )
        
        meals = [{'name': 'New Meal', 'calories': 200, 'mealType': 'breakfast'}]
        
        response = self.client.post(
            reverse('save_meal_history'),
            json.dumps({'meals': meals}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['created'])  # Not created, updated
        
        # Check meal history was updated
        history = MealHistory.objects.get(user=self.user, date=self.today)
        self.assertEqual(history.totalCalories, 200)
    
    def test_get_meal_history_detail_unauthenticated(self):
        """Test getting meal history detail when not authenticated."""
        date_str = self.today.strftime('%Y-%m-%d')
        response = self.client.get(reverse('meal_history_detail', args=[date_str]))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_get_meal_history_detail_authenticated(self):
        """Test getting meal history detail when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create meal history
        MealHistory.objects.create(
            user=self.user,
            date=self.today,
            meals=[
                {'name': 'Breakfast', 'calories': 300, 'mealType': 'breakfast'}
            ],
            totalCalories=300
        )
        
        date_str = self.today.strftime('%Y-%m-%d')
        response = self.client.get(reverse('meal_history_detail', args=[date_str]))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['record'])
        self.assertEqual(data['record']['totalCalories'], 300)
    
    def test_get_meal_history_detail_nonexistent(self):
        """Test getting meal history detail for date with no data."""
        self.client.login(username='testuser', password='testpass123')
        
        yesterday = self.today - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')
        response = self.client.get(reverse('meal_history_detail', args=[date_str]))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIsNone(data['record'])
    
    def test_get_meal_history_detail_invalid_date(self):
        """Test getting meal history detail with invalid date format."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('meal_history_detail', args=['invalid-date']))
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class AIAssistantViewTest(TestCase):
    """Test cases for AI assistant view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.hall = DiningHall.objects.create(
            hallName='Berkshire',
            hours='07:00-20:00',
            meals={
                'breakfast': [{'name': 'Oatmeal', 'calories': 150, 'allergens': [], 'dietTags': ['vegetarian']}],
                'lunch': [],
                'dinner': []
            }
        )
    
    def test_ai_assistant_unauthenticated(self):
        """Test AI assistant when not authenticated."""
        response = self.client.post(reverse('ai_assistant'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    @patch('menus.views.get_recommendations_for_all_dining')
    def test_ai_assistant_authenticated(self, mock_recommendations):
        """Test AI assistant when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock the recommendation function
        mock_recommendations.return_value = {
            'berkshire': ['Oatmeal'],
            'worcester': [],
            'franklin': [],
            'hampshire': []
        }
        
        response = self.client.post(
            reverse('ai_assistant'),
            json.dumps({'message': 'I want something vegetarian'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('response', data)
        self.assertIn('recommendations', data)
        
        # Verify recommendation function was called
        mock_recommendations.assert_called_once()
    
    def test_ai_assistant_empty_message(self):
        """Test AI assistant with empty message."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('ai_assistant'),
            json.dumps({'message': ''}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_ai_assistant_invalid_method(self):
        """Test AI assistant with invalid HTTP method."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('ai_assistant'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
