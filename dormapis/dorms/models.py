from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Sinh viên'),
        ('admin', 'Quản trị viên'),
    )
    phone = models.CharField(max_length=255)
    student_code = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    updated_profile = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    gender = models.CharField(max_length=20,
                              choices=[
                                  ('male', 'Nam'),
                                  ('female', 'Nữ'),
                                  ('other', 'Khác')
                              ],
                            null = True,
                            blank = True
                        )
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    national_code = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"