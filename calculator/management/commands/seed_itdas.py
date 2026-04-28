from django.core.management.base import BaseCommand
from calculator.models import ITDASReference


ITDAS_DATA = [
    ("wheat", "germination", 20, 15, 10, 3000),
    ("wheat", "vegetative", 60, 30, 20, 4000),
    ("wheat", "flowering", 40, 20, 30, 5000),
    ("wheat", "fruiting", 20, 10, 40, 4500),
    ("wheat", "maturation", 0, 5, 20, 2000),

    ("tomato", "germination", 30, 20, 15, 4000),
    ("tomato", "vegetative", 80, 40, 50, 6000),
    ("tomato", "flowering", 60, 30, 60, 7000),
    ("tomato", "fruiting", 40, 20, 80, 8000),
    ("tomato", "maturation", 10, 10, 40, 5000),

    ("olive", "germination", 10, 10, 10, 2000),
    ("olive", "vegetative", 40, 20, 30, 3000),
    ("olive", "flowering", 30, 15, 40, 3500),
    ("olive", "fruiting", 20, 10, 50, 4000),
    ("olive", "maturation", 5, 5, 20, 2000),

    ("date_palm", "germination", 15, 10, 10, 5000),
    ("date_palm", "vegetative", 50, 25, 40, 7000),
    ("date_palm", "flowering", 40, 20, 50, 8000),
    ("date_palm", "fruiting", 30, 15, 60, 9000),
    ("date_palm", "maturation", 10, 10, 30, 6000),

    ("potato", "germination", 40, 30, 20, 4000),
    ("potato", "vegetative", 100, 60, 80, 6000),
    ("potato", "flowering", 80, 40, 100, 7000),
    ("potato", "fruiting", 60, 30, 120, 8000),
    ("potato", "maturation", 10, 10, 50, 4000),

    ("onion", "germination", 20, 15, 10, 3000),
    ("onion", "vegetative", 60, 30, 40, 5000),
    ("onion", "flowering", 40, 20, 50, 6000),
    ("onion", "fruiting", 30, 15, 60, 5500),
    ("onion", "maturation", 5, 5, 20, 3000),

    ("pepper", "germination", 25, 20, 15, 3500),
    ("pepper", "vegetative", 70, 35, 50, 5500),
    ("pepper", "flowering", 50, 25, 60, 6500),
    ("pepper", "fruiting", 40, 20, 70, 7000),
    ("pepper", "maturation", 10, 10, 30, 4000),

    ("watermelon", "germination", 20, 15, 10, 4000),
    ("watermelon", "vegetative", 60, 30, 40, 6000),
    ("watermelon", "flowering", 50, 25, 50, 7000),
    ("watermelon", "fruiting", 40, 20, 60, 8000),
    ("watermelon", "maturation", 10, 10, 25, 5000),

    ("citrus", "germination", 15, 10, 10, 3000),
    ("citrus", "vegetative", 50, 25, 35, 5000),
    ("citrus", "flowering", 40, 20, 45, 6000),
    ("citrus", "fruiting", 30, 15, 55, 7000),
    ("citrus", "maturation", 10, 10, 25, 4000),

    ("barley", "germination", 15, 12, 8, 2500),
    ("barley", "vegetative", 50, 25, 18, 3500),
    ("barley", "flowering", 35, 18, 25, 4000),
    ("barley", "fruiting", 18, 10, 35, 3500),
    ("barley", "maturation", 0, 5, 15, 1500),
]


class Command(BaseCommand):
    help = "Seed ITDAS reference table with NPK and irrigation data for Algeria's 10 key crops"

    def handle(self, *args, **kwargs):
        created = 0
        skipped = 0
        for crop, stage, n, p, k, irr in ITDAS_DATA:
            obj, was_created = ITDASReference.objects.get_or_create(
                crop=crop,
                growth_stage=stage,
                defaults={
                    "npk_n": n,
                    "npk_p": p,
                    "npk_k": k,
                    "irrigation_liters_per_ha_per_day": irr,
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"Done. {created} entries created, {skipped} already existed."))