from django.db import models
from django.contrib.postgres.fields import JSONField  # or models.JSONField if Django ≥ 3.1
from django.core.validators import MaxValueValidator, MinValueValidator
class DiningHall(models.Model):
    hallName = models.CharField(max_length=100)
    hours = models.CharField(max_length=20)  # e.g. "07:00-20:00"
    mealHours = models.JSONField(default=dict, blank=True)
    meals = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.hallName


class Review(models.Model):
    username = models.CharField(max_length=20)
    reviewText = models.CharField(max_length=1000)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    likes = models.IntegerField(default=0)
    diningHall = models.ForeignKey(DiningHall, on_delete=models.CASCADE)
