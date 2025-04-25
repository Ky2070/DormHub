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


class Building(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Room(models.Model):
    GENDER_CHOICES = [
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('all', 'Không giới hạn')
    ]
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    gender_restriction = models.CharField(
        max_length=30,
        choices=GENDER_CHOICES,
        default='all'
    )

    def __str__(self):
        return f"{self.name} - {self.building.name}"

    @property
    def current_students(self):
        return RoomRegistration.objects.filter(room=self, is_active=True).count()

    @property
    def is_full(self):
        return self.current_students >= self.capacity

    @property
    def available_capacity(self):
        current_count = max(self.current_students, 0)
        return max(self.capacity - current_count, 0)


class RoomRegistration(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student.username} - {self.room.name} ({'Active' if self.is_active else 'Inactive'})"

    def save(self, *args, **kwargs):
        if not self.room:
            raise ValueError("Phòng không hợp lệ.")

        if self.room.is_full:
            raise ValueError(f"Phòng {self.room.name} đã đầy, không thể đăng ký thêm")
        super(RoomRegistration, self).save(*args, **kwargs)
