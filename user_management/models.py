from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class User(AbstractUser):
    phone = models.CharField(max_length=15, unique=True)
    is_verified = models.BooleanField(default=False)

class KYCProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bvn = models.CharField(max_length=11, unique=True)
    nin = models.CharField(max_length=11, blank=True, null=True)
    date_of_birth = models.DateField()
    address = models.TextField()
    selfie = models.ImageField(upload_to="kyc/selfies/")
    id_document = models.FileField(upload_to="kyc/ids/")
    is_approved = models.BooleanField(default=False)
