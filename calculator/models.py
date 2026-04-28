from django.db import models


class ITDASReference(models.Model):

    CROPS = [
        ('wheat', 'Wheat'),
        ('tomato', 'Tomato'),
        ('olive', 'Olive'),
        ('date_palm', 'Date Palm'),
        ('potato', 'Potato'),
        ('onion', 'Onion'),
        ('pepper', 'Pepper'),
        ('watermelon', 'Watermelon'),
        ('citrus', 'Citrus'),
        ('barley', 'Barley'),
    ]

    GROWTH_STAGES = [
        ('germination', 'Germination'),
        ('vegetative', 'Vegetative'),
        ('flowering', 'Flowering'),
        ('fruiting', 'Fruiting'),
        ('maturation', 'Maturation'),
    ]

    crop = models.CharField(max_length=20, choices=CROPS)
    growth_stage = models.CharField(max_length=20, choices=GROWTH_STAGES)
    npk_n = models.FloatField(help_text="Nitrogen kg per hectare")
    npk_p = models.FloatField(help_text="Phosphorus kg per hectare")
    npk_k = models.FloatField(help_text="Potassium kg per hectare")
    irrigation_liters_per_ha_per_day = models.FloatField(help_text="Daily irrigation liters per hectare")

    class Meta:
        unique_together = ('crop', 'growth_stage')

    def __str__(self):
        return f"{self.crop} — {self.growth_stage}"