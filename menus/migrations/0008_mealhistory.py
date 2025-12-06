# Generated migration for MealHistory model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('menus', '0007_menuitem_userprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='MealHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(help_text='Date of the meal selection')),
                ('meals', models.JSONField(blank=True, default=list, help_text='List of selected meal items for the day')),
                ('totalCalories', models.IntegerField(default=0, help_text='Total calories consumed for the day')),
                ('primaryHall', models.CharField(blank=True, default='', help_text='Most visited dining hall that day', max_length=100)),
                ('createdAt', models.DateTimeField(auto_now_add=True)),
                ('updatedAt', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meal_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Meal histories',
                'ordering': ['-date'],
                'unique_together': {('user', 'date')},
            },
        ),
    ]
