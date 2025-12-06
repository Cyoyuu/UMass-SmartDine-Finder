"""
Django management command to import menu data from scraped_menus.json into the database.

Usage:
    python manage.py import_menus
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from menus.models import DiningHall
import json
import os


class Command(BaseCommand):
    help = 'Import menu data from scraped_menus.json into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing menu data before importing',
        )

    def handle(self, *args, **options):
        # Get the JSON file path
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data',
            'scraped_menus.json'
        )

        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Reading data from: {json_path}'))

        # Load JSON data
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading JSON file: {e}'))
            return

        # Clear existing data if requested
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing dining hall data...'))
            DiningHall.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared'))

        # Import data within a transaction
        try:
            with transaction.atomic():
                self.import_dining_halls(data)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {e}'))
            raise

        self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))

    def import_dining_halls(self, data):
        """Import dining halls and their menus."""
        dining_halls = data.get('diningHalls', [])
        
        self.stdout.write(f'Importing {len(dining_halls)} dining halls...')
        
        for hall_data in dining_halls:
            hall_name = hall_data.get('hallName')
            
            # Get or create the dining hall
            dining_hall, created = DiningHall.objects.update_or_create(
                hallName=hall_name,
                defaults={
                    'hours': hall_data.get('hours', '07:00-21:00'),
                    'mealHours': hall_data.get('mealHours', {
                        'breakfast': '07:00-10:30',
                        'lunch': '11:00-14:30',
                        'dinner': '17:00-21:00'
                    }),
                    'meals': hall_data.get('meals', {
                        'breakfast': [],
                        'lunch': [],
                        'dinner': []
                    })
                }
            )
            
            action = 'Created' if created else 'Updated'
            meals = hall_data.get('meals', {})
            breakfast_count = len(meals.get('breakfast', []))
            lunch_count = len(meals.get('lunch', []))
            dinner_count = len(meals.get('dinner', []))
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'  {action} {hall_name}: '
                    f'{breakfast_count} breakfast, '
                    f'{lunch_count} lunch, '
                    f'{dinner_count} dinner items'
                )
            )
