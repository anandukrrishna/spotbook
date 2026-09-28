from django.db import models

# Create your models here.

# -----auth-----

class LoginTable(models.Model):
    username=models.CharField(max_length=30, blank=True, null=True)
    password=models.CharField(max_length=128, blank=True, null=True)
    usertype=models.CharField(max_length=20, blank=True, null=True)

class UserTable(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    LOGINID = models.ForeignKey(LoginTable, on_delete=models.CASCADE)