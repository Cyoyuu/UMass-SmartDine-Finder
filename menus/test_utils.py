"""
Test cases for utility functions and helpers in menus app.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

from .models import DiningHall, UserProfile
from .views import (
    get_menu_data_from_db,
    is_hall_open,
    is_weekend,
    get_current_meal_type,
    filter_meals_for_user,
    calculate_hall_score,
    calculate_meal_specific_score,
    filter_meals_by_preferences,
    get_dining_halls_data
)


class MenuDataUtilsTest(TestCase):
    """Test cases for menu data utility functions."""
    
    def setUp(self):
        """Set up test data."""
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
                'lunch': [],
                'dinner': []
            }
        )
    
    def test_get_menu_data_from_db(self):
        """Test getting menu data from database."""
        data = get_menu_data_from_db()
        
        self.assertIn('diningHalls', data)
        self.assertEqual(len(data['diningHalls']), 1)
        self.assertEqual(data['diningHalls'][0]['hallName'], 'Berkshire')
        self.assertIn('allergenCategories', data)
        self.assertIn('dietCategories', data)
    
    def test_get_menu_data_from_db_empty(self):
        """Test getting menu data when no halls exist."""
        DiningHall.objects.all().delete()
        data = get_menu_data_from_db()
        
        self.assertEqual(len(data['diningHalls']), 0)
        self.assertIn('allergenCategories', data)
        self.assertIn('dietCategories', data)


class HallStatusUtilsTest(TestCase):
    """Test cases for hall status utility functions."""
    
    @patch('menus.views.datetime')
    def test_is_hall_open_valid_hours(self, mock_datetime):
        """Test is_hall_open with valid hours string."""
        # Mock current time to be within morning hours
        mock_now = MagicMock()
        mock_now.time.return_value = datetime.strptime('12:00', '%H:%M').time()
        mock_datetime.now.return_value = mock_now
        # Mock strptime to parse the hours string
        def strptime_side_effect(date_string, format_string):
            return datetime.strptime(date_string, format_string)
        mock_datetime.strptime.side_effect = strptime_side_effect
        
        self.assertTrue(is_hall_open('07:00-20:00'))
        
        # Mock current time to be within evening hours
        mock_now.time.return_value = datetime.strptime('18:00', '%H:%M').time()
        self.assertTrue(is_hall_open('17:00-22:00'))
    
    def test_is_hall_open_invalid_hours(self):
        """Test is_hall_open with invalid hours string."""
        self.assertFalse(is_hall_open('invalid'))
        self.assertFalse(is_hall_open(''))
        self.assertFalse(is_hall_open('07:00'))
    
    @patch('menus.views.datetime')
    def test_is_hall_open_time_check(self, mock_datetime):
        """Test is_hall_open with mocked time."""
        # Mock strptime to parse the hours string
        def strptime_side_effect(date_string, format_string):
            return datetime.strptime(date_string, format_string)
        mock_datetime.strptime.side_effect = strptime_side_effect
        
        # Mock current time to be within hours
        mock_now = MagicMock()
        mock_now.time.return_value = datetime.strptime('12:00', '%H:%M').time()
        mock_datetime.now.return_value = mock_now
        
        self.assertTrue(is_hall_open('07:00-20:00'))
        
        # Mock current time to be outside hours
        mock_now.time.return_value = datetime.strptime('06:00', '%H:%M').time()
        self.assertFalse(is_hall_open('07:00-20:00'))
    
    @patch('menus.views.datetime')
    def test_is_weekend(self, mock_datetime):
        """Test is_weekend function."""
        # Mock Saturday (weekday 5)
        mock_now = MagicMock()
        mock_now.weekday.return_value = 5
        mock_datetime.now.return_value = mock_now
        self.assertTrue(is_weekend())
        
        # Mock Sunday (weekday 6)
        mock_now.weekday.return_value = 6
        self.assertTrue(is_weekend())
        
        # Mock Monday (weekday 0)
        mock_now.weekday.return_value = 0
        self.assertFalse(is_weekend())
    
    @patch('menus.views.datetime')
    def test_get_current_meal_type_weekday(self, mock_datetime):
        """Test get_current_meal_type on weekday."""
        # Mock strptime to parse time strings
        def strptime_side_effect(date_string, format_string):
            return datetime.strptime(date_string, format_string)
        mock_datetime.strptime.side_effect = strptime_side_effect
        
        # Mock breakfast time
        mock_now = MagicMock()
        mock_now.time.return_value = datetime.strptime('08:00', '%H:%M').time()
        mock_now.weekday.return_value = 0  # Monday
        mock_datetime.now.return_value = mock_now
        
        self.assertEqual(get_current_meal_type(), 'breakfast')
        
        # Mock lunch time
        mock_now.time.return_value = datetime.strptime('12:00', '%H:%M').time()
        self.assertEqual(get_current_meal_type(), 'lunch')
        
        # Mock dinner time
        mock_now.time.return_value = datetime.strptime('18:00', '%H:%M').time()
        self.assertEqual(get_current_meal_type(), 'dinner')
    
    @patch('menus.views.datetime')
    def test_get_current_meal_type_weekend(self, mock_datetime):
        """Test get_current_meal_type on weekend."""
        # Mock strptime to parse time strings
        def strptime_side_effect(date_string, format_string):
            return datetime.strptime(date_string, format_string)
        mock_datetime.strptime.side_effect = strptime_side_effect
        
        # Mock weekend lunch time
        mock_now = MagicMock()
        mock_now.time.return_value = datetime.strptime('12:00', '%H:%M').time()
        mock_now.weekday.return_value = 5  # Saturday
        mock_datetime.now.return_value = mock_now
        
        self.assertEqual(get_current_meal_type(), 'lunch')
        
        # Mock weekend dinner time
        mock_now.time.return_value = datetime.strptime('18:00', '%H:%M').time()
        self.assertEqual(get_current_meal_type(), 'dinner')


class MealFilteringUtilsTest(TestCase):
    """Test cases for meal filtering utility functions."""
    
    def setUp(self):
        """Set up test data."""
        self.meals = {
            'breakfast': [
                {'name': 'Oatmeal', 'calories': 150, 'allergens': [], 'dietTags': ['vegetarian']},
                {'name': 'Eggs', 'calories': 200, 'allergens': ['eggs'], 'dietTags': []}
            ],
            'lunch': [
                {'name': 'Salad', 'calories': 100, 'allergens': [], 'dietTags': ['vegetarian']},
                {'name': 'Chicken', 'calories': 250, 'allergens': ['eggs'], 'dietTags': ['halal']}
            ],
            'dinner': []
        }
    
    def test_filter_meals_for_user_no_preferences(self):
        """Test filtering meals with no user preferences."""
        filtered = filter_meals_for_user(self.meals)
        
        self.assertEqual(len(filtered['breakfast']), 2)
        self.assertEqual(len(filtered['lunch']), 2)
        self.assertEqual(len(filtered['dinner']), 0)
    
    def test_filter_meals_for_user_with_allergens(self):
        """Test filtering meals with allergen restrictions."""
        filtered = filter_meals_for_user(self.meals, user_allergens=['eggs'])
        
        # Should exclude items with eggs
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(filtered['breakfast'][0]['name'], 'Oatmeal')
        self.assertEqual(len(filtered['lunch']), 1)
        self.assertEqual(filtered['lunch'][0]['name'], 'Salad')
    
    def test_filter_meals_for_user_old_format(self):
        """Test filtering meals with old string format."""
        old_format_meals = {
            'breakfast': ['Item1', 'Item2'],
            'lunch': [],
            'dinner': []
        }
        filtered = filter_meals_for_user(old_format_meals)
        
        self.assertEqual(len(filtered['breakfast']), 2)
        # Should convert to dict format
        self.assertIsInstance(filtered['breakfast'][0], dict)
    
    def test_filter_meals_by_preferences_no_preferences(self):
        """Test filter_meals_by_preferences with no user preferences."""
        filtered = filter_meals_by_preferences(self.meals, [], [])
        
        self.assertEqual(len(filtered['breakfast']), 2)
        self.assertEqual(len(filtered['lunch']), 2)
    
    def test_filter_meals_by_preferences_with_allergens(self):
        """Test filter_meals_by_preferences with allergen restrictions."""
        filtered = filter_meals_by_preferences(self.meals, ['eggs'], [])
        
        # Should exclude items with eggs
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(len(filtered['lunch']), 1)
    
    def test_filter_meals_by_preferences_with_diet(self):
        """Test filter_meals_by_preferences with diet preferences."""
        filtered = filter_meals_by_preferences(self.meals, [], ['vegetarian'])
        
        # Should only include items matching diet preference
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(filtered['breakfast'][0]['name'], 'Oatmeal')
        self.assertEqual(len(filtered['lunch']), 1)
        self.assertEqual(filtered['lunch'][0]['name'], 'Salad')
    
    def test_filter_meals_by_preferences_combined(self):
        """Test filter_meals_by_preferences with both allergens and diet."""
        filtered = filter_meals_by_preferences(self.meals, ['eggs'], ['vegetarian'])
        
        # Should exclude items with allergens AND only show diet matches
        self.assertEqual(len(filtered['breakfast']), 1)
        self.assertEqual(len(filtered['lunch']), 1)
        self.assertEqual(filtered['lunch'][0]['name'], 'Salad')
    
    def test_filter_meals_by_preferences_diet_categories(self):
        """Test filter_meals_by_preferences with dietCategories field."""
        meals_with_diet_categories = {
            'breakfast': [
                {'name': 'Oatmeal', 'calories': 150, 'allergens': [], 'dietCategories': ['vegetarian']}
            ],
            'lunch': [],
            'dinner': []
        }
        filtered = filter_meals_by_preferences(meals_with_diet_categories, [], ['vegetarian'])
        
        self.assertEqual(len(filtered['breakfast']), 1)


class ScoringUtilsTest(TestCase):
    """Test cases for scoring utility functions."""
    
    def setUp(self):
        """Set up test data."""
        self.hall_data = {
            'hallName': 'Berkshire',
            'hours': '07:00-20:00',
            'isOpen': True,
            'meals': {
                'breakfast': [
                    {'name': 'Oatmeal', 'calories': 150, 'allergens': [], 'dietTags': ['vegetarian']},
                    {'name': 'Eggs', 'calories': 200, 'allergens': ['eggs'], 'dietTags': []}
                ],
                'lunch': [
                    {'name': 'Salad', 'calories': 100, 'allergens': [], 'dietTags': ['vegetarian']}
                ],
                'dinner': []
            }
        }
    
    def test_calculate_hall_score_no_preferences(self):
        """Test calculate_hall_score with no user preferences."""
        score, matching_items, total_calories, match_rate = calculate_hall_score(self.hall_data)
        
        self.assertGreater(score, 0)
        self.assertEqual(matching_items, 3)  # All items are safe
        self.assertEqual(total_calories, 450)
        self.assertGreater(match_rate, 0)
    
    def test_calculate_hall_score_with_allergens(self):
        """Test calculate_hall_score with allergen restrictions."""
        score, matching_items, total_calories, match_rate = calculate_hall_score(
            self.hall_data, user_allergens=['eggs']
        )
        
        # Should exclude Eggs item
        self.assertEqual(matching_items, 2)
        self.assertEqual(total_calories, 250)
    
    def test_calculate_hall_score_with_diet_preferences(self):
        """Test calculate_hall_score with diet preferences."""
        score, matching_items, total_calories, match_rate = calculate_hall_score(
            self.hall_data, user_diet_prefs=['vegetarian']
        )
        
        # All items are safe, some match diet
        self.assertGreater(score, 0)
        self.assertEqual(matching_items, 3)
    
    def test_calculate_hall_score_closed_hall(self):
        """Test calculate_hall_score for closed hall."""
        closed_hall = self.hall_data.copy()
        closed_hall['isOpen'] = False
        
        score_open, _, _, _ = calculate_hall_score(self.hall_data)
        score_closed, _, _, _ = calculate_hall_score(closed_hall)
        
        # Open hall should have higher score (bonus points)
        self.assertGreater(score_open, score_closed)
    
    def test_calculate_meal_specific_score(self):
        """Test calculate_meal_specific_score."""
        score, safe_items, match_rate = calculate_meal_specific_score(
            self.hall_data, 'breakfast'
        )
        
        self.assertGreater(score, 0)
        self.assertEqual(safe_items, 2)  # Both breakfast items are safe (no allergens in user prefs)
        self.assertGreater(match_rate, 0)
    
    def test_calculate_meal_specific_score_with_allergens(self):
        """Test calculate_meal_specific_score with allergen restrictions."""
        score, safe_items, match_rate = calculate_meal_specific_score(
            self.hall_data, 'breakfast', user_allergens=['eggs']
        )
        
        # Should exclude Eggs item
        self.assertEqual(safe_items, 1)
        self.assertEqual(match_rate, 50)  # 1 out of 2 items is safe
    
    def test_calculate_meal_specific_score_with_diet(self):
        """Test calculate_meal_specific_score with diet preferences."""
        score, safe_items, match_rate = calculate_meal_specific_score(
            self.hall_data, 'breakfast', user_diet_prefs=['vegetarian']
        )
        
        self.assertEqual(safe_items, 2)
        self.assertGreater(match_rate, 0)
    
    def test_calculate_meal_specific_score_empty_meal(self):
        """Test calculate_meal_specific_score with empty meal."""
        empty_hall = {
            'meals': {'breakfast': [], 'lunch': [], 'dinner': []},
            'isOpen': True
        }
        
        score, safe_items, match_rate = calculate_meal_specific_score(empty_hall, 'breakfast')
        
        self.assertEqual(score, 50)  # Only open bonus
        self.assertEqual(safe_items, 0)
        self.assertEqual(match_rate, 0)


class GetDiningHallsDataTest(TestCase):
    """Test cases for get_dining_halls_data function."""
    
    def setUp(self):
        """Set up test data."""
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
                'lunch': [],
                'dinner': []
            }
        )
    
    def test_get_dining_halls_data_no_user(self):
        """Test get_dining_halls_data with no authenticated user."""
        halls_data = get_dining_halls_data()
        
        self.assertEqual(len(halls_data), 1)
        self.assertEqual(halls_data[0]['hallName'], 'Berkshire')
        self.assertIn('meals', halls_data[0])
        self.assertIn('isOpen', halls_data[0])
        self.assertIn('reviews', halls_data[0])
    
    def test_get_dining_halls_data_with_user(self):
        """Test get_dining_halls_data with authenticated user."""
        halls_data = get_dining_halls_data(current_user=self.user)
        
        self.assertEqual(len(halls_data), 1)
        self.assertIn('score', halls_data[0])
        self.assertIn('matchingItems', halls_data[0])
    
    def test_get_dining_halls_data_with_profile(self):
        """Test get_dining_halls_data with user profile."""
        profile = self.user.profile
        profile.allergens = ['eggs']
        profile.dietPreferences = ['vegetarian']
        profile.save()
        
        halls_data = get_dining_halls_data(current_user=self.user, include_filtered=True)
        
        self.assertEqual(len(halls_data), 1)
        self.assertIn('filteredMeals', halls_data[0])
        # Filtered meals should exclude items with eggs
        filtered = halls_data[0]['filteredMeals']
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            items = filtered.get(meal_type, [])
            for item in items:
                if isinstance(item, dict):
                    self.assertNotIn('eggs', item.get('allergens', []))
    
    def test_get_dining_halls_data_with_reviews(self):
        """Test get_dining_halls_data with reviews."""
        from .models import Review
        
        Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='Great!',
            rating=5
        )
        
        halls_data = get_dining_halls_data(current_user=self.user)
        
        self.assertEqual(len(halls_data), 1)
        self.assertEqual(len(halls_data[0]['reviews']), 1)
        self.assertEqual(halls_data[0]['reviewCount'], 1)
        self.assertEqual(halls_data[0]['avgRating'], 5.0)
        self.assertIsNotNone(halls_data[0]['userReview'])
    
    def test_get_dining_halls_data_multiple_reviews(self):
        """Test get_dining_halls_data with multiple reviews."""
        from .models import Review
        
        user2 = User.objects.create_user(
            username='testuser2',
            password='testpass123'
        )
        
        Review.objects.create(
            user=self.user,
            diningHall=self.hall,
            reviewText='Great!',
            rating=5
        )
        Review.objects.create(
            user=user2,
            diningHall=self.hall,
            reviewText='Good!',
            rating=4
        )
        
        halls_data = get_dining_halls_data(current_user=self.user)
        
        self.assertEqual(len(halls_data), 1)
        self.assertEqual(halls_data[0]['reviewCount'], 2)
        self.assertEqual(halls_data[0]['avgRating'], 4.5)  # (5+4)/2
        self.assertIsNotNone(halls_data[0]['userReview'])

