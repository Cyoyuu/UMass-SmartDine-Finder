from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError

from accounts.models import UserFoodPreference


class UserFoodPreferenceModelTest(TestCase):
    """Test cases for UserFoodPreference model."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_food_preference_creation(self):
        """Test creating a UserFoodPreference."""
        preference = UserFoodPreference.objects.create(
            user=self.user,
            data={'diet': 'vegetarian', 'allergens': ['dairy']}
        )
        self.assertEqual(preference.user, self.user)
        self.assertEqual(preference.data['diet'], 'vegetarian')
        self.assertEqual(preference.data['allergens'], ['dairy'])
    
    def test_user_food_preference_one_to_one(self):
        """Test that UserFoodPreference has one-to-one relationship with User."""
        preference1 = UserFoodPreference.objects.create(
            user=self.user,
            data={}
        )
        # Should not be able to create another preference for same user
        # Django will raise IntegrityError at database level
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            UserFoodPreference.objects.create(
                user=self.user,
                data={}
            )
    
    def test_user_food_preference_str(self):
        """Test UserFoodPreference string representation."""
        preference = UserFoodPreference.objects.create(
            user=self.user,
            data={}
        )
        self.assertEqual(str(preference), "testuser preferences")
    
    def test_user_food_preference_default_data(self):
        """Test default data value."""
        preference = UserFoodPreference.objects.create(user=self.user)
        self.assertEqual(preference.data, {})
    
    def test_user_food_preference_data_storage(self):
        """Test storing complex JSON data."""
        complex_data = {
            'diet': 'vegetarian',
            'allergens': ['dairy', 'eggs'],
            'goals': ['high_protein'],
            'likes': 'spicy, sweet',
            'dislikes': 'bitter'
        }
        preference = UserFoodPreference.objects.create(
            user=self.user,
            data=complex_data
        )
        preference.refresh_from_db()
        self.assertEqual(preference.data, complex_data)


class HomeViewTest(TestCase):
    """Test cases for home view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_home_view_get(self):
        """Test accessing home page."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
    
    def test_home_view_with_dining_halls(self):
        """Test home view with dining halls data."""
        from menus.models import DiningHall
        
        DiningHall.objects.create(
            hallName='Berkshire',
            hours='07:00-20:00',
            meals={
                'breakfast': [{'name': 'Oatmeal', 'calories': 150}],
                'lunch': [],
                'dinner': []
            }
        )
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('dining_hall_data', response.context)
        self.assertIn('dining_halls_list', response.context)


class RegisterViewTest(TestCase):
    """Test cases for registration view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_register_view_get(self):
        """Test accessing registration page."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
    
    def test_register_view_post_success(self):
        """Test successful user registration."""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!'
        })
        
        # Should redirect to home
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/'))
        
        # User should be created
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # User should be logged in
        response = self.client.get(reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_register_view_post_invalid(self):
        """Test registration with invalid data."""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'pass1',
            'password2': 'pass2'  # Mismatched passwords
        })
        
        # Should stay on registration page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
        
        # User should not be created
        self.assertFalse(User.objects.filter(username='newuser').exists())


class SurveyViewTest(TestCase):
    """Test cases for survey view."""
    
    def setUp(self):
        """Set up test user and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_survey_view_get_authenticated(self):
        """Test accessing survey page when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('survey'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/survey.html')
    
    def test_survey_view_get_unauthenticated(self):
        """Test accessing survey page when not authenticated."""
        response = self.client.get(reverse('survey'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_survey_view_post(self):
        """Test submitting survey form."""
        self.client.login(username='testuser', password='testpass123')
        
        from menus.models import UserProfile
        
        response = self.client.post(reverse('survey'), {
            'allergens': ['dairy', 'gluten'],
            'calorieTarget': 1800,
            'dietPreferences': ['vegetarian', 'halal']
        })
        
        # Should redirect to recommendations
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('recommendations'))
        
        # Profile should be updated
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.allergens, ['dairy', 'gluten'])
        self.assertEqual(profile.calorieTarget, 1800)
        self.assertEqual(profile.dietPreferences, ['vegetarian', 'halal'])
        self.assertTrue(profile.surveyCompleted)
    
    def test_survey_view_creates_profile(self):
        """Test that survey view creates profile if it doesn't exist."""
        self.client.login(username='testuser', password='testpass123')
        
        from menus.models import UserProfile
        
        # Delete profile if exists
        UserProfile.objects.filter(user=self.user).delete()
        
        response = self.client.get(reverse('survey'))
        self.assertEqual(response.status_code, 200)
        
        # Profile should be created
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())


class SkipSurveyViewTest(TestCase):
    """Test cases for skip survey view."""
    
    def setUp(self):
        """Set up test user and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_skip_survey_unauthenticated(self):
        """Test skip survey when not authenticated."""
        response = self.client.get(reverse('skip_survey'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_skip_survey_authenticated(self):
        """Test skipping survey when authenticated."""
        self.client.login(username='testuser', password='testpass123')
        
        from menus.models import UserProfile
        
        response = self.client.get(reverse('skip_survey'))
        
        # Should redirect to recommendations
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('recommendations'))
        
        # Profile should be marked as completed
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.surveyCompleted)
    
    def test_skip_survey_creates_profile(self):
        """Test that skip survey creates profile if it doesn't exist."""
        self.client.login(username='testuser', password='testpass123')
        
        from menus.models import UserProfile
        
        # Delete profile if exists
        UserProfile.objects.filter(user=self.user).delete()
        
        response = self.client.get(reverse('skip_survey'))
        self.assertEqual(response.status_code, 302)
        
        # Profile should be created
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.surveyCompleted)


class LogoutViewTest(TestCase):
    """Test cases for logout view."""
    
    def setUp(self):
        """Set up test user and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_logout_view(self):
        """Test logout functionality."""
        # Login first
        self.client.login(username='testuser', password='testpass123')
        
        # Verify logged in
        response = self.client.get(reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        
        # Logout
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))
        
        # Verify logged out
        response = self.client.get(reverse('home'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)
