from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings


class GalleryPhoto(models.Model):

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

    WILAYAS = [
        ('adrar', 'Adrar'), ('chlef', 'Chlef'), ('laghouat', 'Laghouat'),
        ('oum_el_bouaghi', 'Oum El Bouaghi'), ('batna', 'Batna'), ('bejaia', 'Béjaïa'),
        ('biskra', 'Biskra'), ('bechar', 'Béchar'), ('blida', 'Blida'),
        ('bouira', 'Bouira'), ('tamanrasset', 'Tamanrasset'), ('tebessa', 'Tébessa'),
        ('tlemcen', 'Tlemcen'), ('tiaret', 'Tiaret'), ('tizi_ouzou', 'Tizi Ouzou'),
        ('alger', 'Alger'), ('djelfa', 'Djelfa'), ('jijel', 'Jijel'),
        ('setif', 'Sétif'), ('saida', 'Saïda'), ('skikda', 'Skikda'),
        ('sidi_bel_abbes', 'Sidi Bel Abbès'), ('annaba', 'Annaba'), ('guelma', 'Guelma'),
        ('constantine', 'Constantine'), ('medea', 'Médéa'), ('mostaganem', 'Mostaganem'),
        ('msila', 'M\'Sila'), ('mascara', 'Mascara'), ('ouargla', 'Ouargla'),
        ('oran', 'Oran'), ('el_bayadh', 'El Bayadh'), ('illizi', 'Illizi'),
        ('bordj_bou_arreridj', 'Bordj Bou Arréridj'), ('boumerdes', 'Boumerdès'),
        ('el_tarf', 'El Tarf'), ('tindouf', 'Tindouf'), ('tissemsilt', 'Tissemsilt'),
        ('el_oued', 'El Oued'), ('khenchela', 'Khenchela'), ('souk_ahras', 'Souk Ahras'),
        ('tipaza', 'Tipaza'), ('mila', 'Mila'), ('ain_defla', 'Aïn Defla'),
        ('naama', 'Naâma'), ('ain_temouchent', 'Aïn Témouchent'), ('ghardaia', 'Ghardaïa'),
        ('relizane', 'Relizane'),
    ]

    image = models.ImageField(upload_to='gallery/')
    crop = models.CharField(max_length=20, choices=CROPS)
    wilaya = models.CharField(max_length=50, choices=WILAYAS)
    disease_tag = models.CharField(max_length=100, blank=True)
    is_approved = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop} — {self.wilaya} — {self.submitted_at.date()}"