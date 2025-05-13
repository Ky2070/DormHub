from django.db import models
from django.contrib.auth.models import AbstractUser
from decimal import Decimal
# Create your models here.


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Sinh viên'),
        ('admin', 'Quản trị viên'),
    )
    phone = models.CharField(max_length=100, null=True, blank=True)
    student_code = models.CharField(max_length=100, blank=True, null=True, unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    updated_profile = models.DateTimeField(null=True, blank=True)
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


class FCMDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_devices')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.token[:10]}..."


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


class RoomSwap(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_swaps', limit_choices_to={'role': 'student'})
    current_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='current_room')
    desired_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='desired_room')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_swaps',
                                     limit_choices_to={'role__in': ['admin', 'manager']})
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Yêu cầu đổi phòng của {self.student.username} - {self.created_at.strftime('%d/%m/%Y')}"


class FeeType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_recurring = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    billing_period = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('room', 'billing_period')  # Mỗi phòng chỉ có 1 hóa đơn/tháng

    def __str__(self):
        return f"Hóa đơn phòng {self.room.name} - {self.billing_period.strftime('%m/%Y')}"

    @property
    def total_amount(self):
        return sum(
            (detail.amount or Decimal('0.00')) for detail in self.invoice_details.all()
        )


class InvoiceDetail(models.Model):
    UNIT_CHOICES = [
        ('kWh', 'kWh - Điện năng'),
        ('m³', 'm³ - Nước'),
        ('người', 'Người'),
        ('tháng', 'Tháng'),
    ]
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='invoice_details'
    )
    fee_type = models.ForeignKey(
        FeeType,
        on_delete=models.CASCADE
    )
    quantity = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=30,
                            choices=UNIT_CHOICES,
                            null=True, blank=True)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, blank=True  # Giá đơn vị tính phí (ví dụ: giá kWh)
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    description = models.TextField(
        blank=True,
        null=True
    )

    def get_total_amount(self):
        """Tính tổng tiền cho từng loại phí, dựa trên số lượng và đơn giá"""
        if self.quantity and self.unit_price:
            return self.quantity * self.unit_price
        return 0

    def __str__(self):
        return f"{self.fee_type.name} - {self.amount}đ"

    class Meta:
        unique_together = ('invoice', 'fee_type')


class NotificationType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Notification(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    notification_type = models.ForeignKey(NotificationType, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_notifications')
    target_users = models.ManyToManyField(User, related_name='notifications')
    is_urgent = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"


class SupportRequest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.student.username}"


class SupportResponse(models.Model):
    request = models.ForeignKey(SupportRequest, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'admin'})
    content = models.TextField()
    responded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Phản hồi từ {self.responder} - {self.request.title}"


class Survey(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'admin'})
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return self.title


class SurveyQuestion(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()

    def __str__(self):
        return self.question_text


class SurveyResponse(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
    answer = models.TextField()

    class Meta:
        unique_together = ('student', 'question')

    def __str__(self):
        return f"{self.student.username} - {self.question.question_text}"
