from rest_framework import serializers
from .models import User
import re
from django.utils import timezone
from datetime import date


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


class UpdateProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'avatar', 'gender', 'date_of_birth', 'address', 'national_code', 'student_code', 'password']

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