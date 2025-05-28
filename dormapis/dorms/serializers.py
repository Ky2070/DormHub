from rest_framework import serializers
from .models import User, Room, RoomRegistration, RoomSwap, Building, Invoice, InvoiceDetail, PaymentMethod, FCMDevice
import re
from django.utils import timezone
from datetime import date
from decimal import Decimal


class BaseSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        d = super().to_representation(instance)
        d['image'] = instance.image.url
        return d


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password', 'avatar']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        print(u.password)
        u.set_password(u.password)
        u.save()

        return u

    def to_representation(self, instance):
        d = super().to_representation(instance)
        d['avatar'] = instance.avatar.url if instance.avatar else ''
        return d


class UpdateProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'avatar', 'gender', 'date_of_birth', 'address', 'national_code',
                  'student_code', 'password']

    def validate_phone(self, value):
        # Ví dụ: Validate số điện thoại chỉ chứa số và 10-11 ký tự
        if not re.match(r'^\d{10,11}$', value):
            raise serializers.ValidationError("Số điện thoại không hợp lệ.")
        return value

    def validate_gender(self, value):
        # Giả sử chỉ cho phép 'male', 'female', 'other'
        if value not in ['male', 'female', 'other']:
            raise serializers.ValidationError("Giới tính không hợp lệ.")
        return value

    def validate_national_code(self, value):
        # Ví dụ: CCCD chỉ được 12 số
        if not re.match(r'^\d{12}$', value):
            raise serializers.ValidationError("Mã quốc gia/CCCD không hợp lệ.")
        return value

    def validate_date_of_birth(self, value):
        if value:
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 18:
                raise serializers.ValidationError("Bạn phải đủ 18 tuổi để cập nhật hồ sơ.")
        return value

    def update(self, instance, validated_data):
        # Update thông tin người dùng
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)

        instance.profile_updated_at = timezone.now()
        instance.save()
        return instance


class RoomSerializer(BaseSerializer):
    current_students = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    available_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'name', 'building', 'description', 'image', 'capacity', 'gender_restriction',
                  'current_students', 'is_full', 'available_capacity']


class RegisterRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomRegistration
        fields = ['id', 'room', 'start_date']

    def validate(self, data):
        user = self.context['request'].user
        room = data['room']

        if room.is_full:
            raise serializers.ValidationError("{room.name} đã đầy")

        already_registered = RoomRegistration.objects.filter(
            student=user,
            is_active=True
        ).exists()

        if already_registered:
            raise serializers.ValidationError(
                "Bạn đã đăng ký phòng rồi. Nếu muốn chuyển phòng, hãy gửi yêu cầu chuyển phòng để được duyệt."
            )

        if hasattr(user, 'gender') and hasattr(room, 'gender_restriction'):
            if user.gender != room.gender_restriction:
                raise serializers.ValidationError(
                    f"{room.name} chỉ dành cho {room.gender_restriction}, bạn không đủ điều kiện."
                )

        return data


class RoomSwapSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomSwap
        fields = ['id', 'student', 'current_room', 'desired_room', 'reason', 'is_approved', 'processed_by',
                  'processed_at']

    def validate_desired_room(self, desired_room):
        request = self.context.get('request')
        student = request.user if request else None

        if not student:
            raise serializers.ValidationError("Không xác định được sinh viên.")

        if desired_room.is_full:
            raise serializers.ValidationError(f"Phòng {desired_room.name} đã đầy, vui lòng chọn phòng khác.")

        current_registration = RoomRegistration.objects.filter(
            student=student, is_active=True
        ).first()

        if current_registration and current_registration.room == desired_room:
            raise serializers.ValidationError("Bạn đang ở phòng này rồi.")

        # ✅ Kiểm tra giới tính phòng và sinh viên
        if hasattr(student, 'gender') and hasattr(desired_room, 'gender_restriction'):
            if student.gender != desired_room.gender_restriction:
                raise serializers.ValidationError(
                    f"Phòng {desired_room.name} dành cho {desired_room.gender_restriction}, bạn không được phép chuyển tới."
                )

        return desired_room


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ['id', 'name', 'address']


class BuildingDetailSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(source='room_set', many=True, read_only=True)

    class Meta:
        model = Building
        fields = ['id', 'name', 'address', 'rooms']


class InvoiceDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceDetail
        fields = '__all__'
        extra_kwargs = {
            'amount': {'read_only': True}
        }

    def validate(self, attrs):
        quantity = Decimal(str(attrs.get('quantity', 0) or 0))
        unit_price = attrs.get('unit_price', Decimal('0.0')) or Decimal('0.0')
        attrs['amount'] = quantity * unit_price
        return attrs

    def create(self, validated_data):
        quantity = Decimal(str(validated_data.get('quantity', 0) or 0))
        unit_price = validated_data.get('unit_price', Decimal('0.0')) or Decimal('0.0')
        validated_data['amount'] = quantity * unit_price
        return super().create(validated_data)


class InvoiceSerializer(serializers.ModelSerializer):
    invoice_details = InvoiceDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class InvoicePaySerializer(serializers.Serializer):
    payment_method = serializers.PrimaryKeyRelatedField(queryset=PaymentMethod.objects.filter(active=True))


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ['token']
