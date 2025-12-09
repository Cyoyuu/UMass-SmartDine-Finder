# Testing Guide

This document provides information about the test suite for the UMass SmartDine Finder project.

## Overview

The project includes comprehensive test coverage for:
- **Models**: UserProfile, MenuItem, DiningHall, Review, MealHistory, UserFoodPreference
- **Views**: Authentication, home, survey, menu, recommendations, reviews, meal history, AI assistant
- **Utilities**: Menu filtering, scoring, hall status checks, meal type detection

## Test Files

### Accounts App Tests
- `accounts/tests.py` - Tests for accounts app models and views
  - UserFoodPreference model tests
  - Home view tests
  - Registration view tests
  - Survey view tests
  - Logout view tests

### Menus App Tests
- `menus/tests.py` - Tests for menus app models and views
  - UserProfile model tests
  - MenuItem model tests
  - DiningHall model tests
  - Review model tests
  - MealHistory model tests
  - Menu view tests
  - Recommendations view tests
  - Review API tests
  - Meal history API tests
  - AI assistant API tests

- `menus/test_utils.py` - Tests for utility functions
  - Menu data loading tests
  - Hall status utility tests
  - Meal filtering tests
  - Scoring function tests
  - Dining halls data aggregation tests

## Running Tests

### Activate Virtual Environment

First, activate your virtual environment:

```bash
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### Run All Tests

Run all tests in the project:

```bash
python manage.py test
```

### Run Tests for Specific App

Run all tests for a specific app:

```bash
python manage.py test accounts
python manage.py test menus
```

### Run Specific Test File

Run tests from a specific test file:

```bash
python manage.py test accounts.tests
python manage.py test menus.tests
python manage.py test menus.test_utils
```

### Run Specific Test Class

Run a specific test class:

```bash
python manage.py test accounts.tests.UserFoodPreferenceModelTest
python manage.py test menus.tests.UserProfileModelTest
```

### Run Specific Test Method

Run a specific test method:

```bash
python manage.py test accounts.tests.UserFoodPreferenceModelTest.test_user_food_preference_creation
python manage.py test menus.tests.UserProfileModelTest.test_user_profile_auto_created
```

### Verbose Output

For more detailed output, use the `--verbosity` flag:

```bash
python manage.py test --verbosity=2
```

### Keep Test Database

To keep the test database after running tests (useful for debugging):

```bash
python manage.py test --keepdb
```

### Parallel Test Execution

For faster test execution on multi-core systems:

```bash
python manage.py test --parallel
```

## Test Coverage

The test suite covers:

1. **Model Tests**
   - Model creation and validation
   - Field constraints and validators
   - Model methods and properties
   - Relationships between models
   - Unique constraints
   - String representations

2. **View Tests**
   - Authentication requirements
   - Template rendering
   - Context data
   - Form submission
   - Redirects
   - JSON responses for API endpoints
   - Error handling

3. **Utility Function Tests**
   - Data filtering and transformation
   - Scoring algorithms
   - Time-based logic
   - Status checking

## Writing New Tests

When adding new features, follow these guidelines:

1. **Test Structure**
   - Use descriptive test class names ending with `Test`
   - Use descriptive test method names starting with `test_`
   - Include docstrings explaining what each test does

2. **Setup and Teardown**
   - Use `setUp()` method to create test data
   - Use `setUpTestData()` for class-level data (Django 1.8+)
   - Clean up after tests if needed

3. **Test Data**
   - Use factories or fixtures for complex data
   - Keep test data minimal but realistic
   - Isolate test data from other tests

4. **Assertions**
   - Use specific assertions (`assertEqual`, `assertIn`, etc.)
   - Test both positive and negative cases
   - Test edge cases and error conditions

5. **Mocking**
   - Mock external API calls
   - Mock time-dependent functions when testing time-based logic
   - Use `unittest.mock` for mocking

## Example Test Structure

```python
from django.test import TestCase
from django.contrib.auth.models import User

class MyModelTest(TestCase):
    """Test cases for MyModel."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_model_creation(self):
        """Test creating a model instance."""
        # Test implementation
        pass
    
    def test_model_method(self):
        """Test a model method."""
        # Test implementation
        pass
```

## Common Issues

### Database Errors
If you encounter database-related errors:
- Make sure migrations are up to date: `python manage.py migrate`
- Try deleting test database: `python manage.py test --keepdb` (then delete manually)

### Import Errors
If you encounter import errors:
- Ensure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`
- Check that all apps are in `INSTALLED_APPS` in `settings.py`

### Test Isolation
Tests should be isolated and not depend on each other. Django's `TestCase` automatically:
- Wraps each test in a transaction
- Rolls back changes after each test
- Provides a fresh database for each test run

## Continuous Integration

For CI/CD pipelines, you can run tests with:

```bash
python manage.py test --no-input --verbosity=2
```

This ensures tests run without user interaction and provide detailed output.

