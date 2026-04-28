from django.db import models
from django.conf import settings
import uuid

class Post(models.Model):
    CROPS = [
        ('wheat', 'Wheat'), ('tomato', 'Tomato'), ('olive', 'Olive'),
        ('date_palm', 'Date Palm'), ('potato', 'Potato'), ('onion', 'Onion'),
        ('pepper', 'Pepper'), ('watermelon', 'Watermelon'), ('citrus', 'Citrus'), ('barley', 'Barley'),
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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    caption = models.TextField(blank=True, default='')
    crop = models.CharField(max_length=20, choices=CROPS)
    wilaya = models.CharField(max_length=50, choices=WILAYAS)
    disease_tag = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Post {self.id} - {self.crop} @ {self.wilaya}"

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='gallery/post_images/')
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"Image {self.order} for Post {self.post.id}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on Post {self.post.id}"