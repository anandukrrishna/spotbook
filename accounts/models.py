from django.db import models

# Create your models here.

# -----auth-----

class LoginTable(models.Model):
    username=models.CharField(max_length=30, blank=True, null=True)
    password=models.CharField(max_length=20, blank=True, null=True)
    usertype=models.CharField(max_length=20, blank=True, null=True)