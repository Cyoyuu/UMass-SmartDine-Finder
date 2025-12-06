from django import forms

DIET_CHOICES = [
    ("none", "No Restriction"),
    ("vegetarian", "Vegetarian"),
    ("vegan", "Vegan"),
    ("halal", "Halal"),
    ("kosher", "Kosher"),
    ("gluten_free", "Gluten Free"),
]

GOAL_CHOICES = [
    ("high_protein", "High Protein"),
    ("low_carb", "Low Carb"),
    ("low_fat", "Low Fat"),
    ("low_calorie", "Low Calorie"),
    ("muscle_gain", "Muscle Gain"),
    ("fat_loss", "Fat Loss"),
]

ALLERGEN_CHOICES = [
    ("milk", "Milk"),
    ("eggs", "Eggs"),
    ("soy", "Soy"),
    ("wheat", "Wheat"),
    ("tree_nuts", "Tree Nuts"),
    ("peanuts", "Peanuts"),
    ("fish", "Fish"),
    ("shellfish", "Shellfish"),
    ("gluten", "Gluten"),
    ("corn", "Corn"),
]

INGREDIENT_AVOID_CHOICES = [
    ("garlic", "Garlic"),
    ("onion", "Onion"),
    ("pork", "Pork"),
    ("beef", "Beef"),
    ("fried", "Fried Food"),
    ("spicy", "Spicy Food"),
]

class FoodPreferenceForm(forms.Form):

    diet = forms.ChoiceField(
        choices=DIET_CHOICES,
        required=False,
        label="Diet Preference"
    )

    avoid_allergens = forms.MultipleChoiceField(
        choices=ALLERGEN_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Allergies"
    )

    avoid_ingredients = forms.MultipleChoiceField(
        choices=INGREDIENT_AVOID_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Ingredients to Avoid"
    )

    goals = forms.MultipleChoiceField(
        choices=GOAL_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Health Goals"
    )

    likes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional: spicy, sweet, crunchy…"}),
        label="Optional Food Likes"
    )

    dislikes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional: things you generally dislike"}),
        label="Optional Food Dislikes"
    )
