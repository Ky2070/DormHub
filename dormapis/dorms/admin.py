from django.contrib import admin
from .models import Building, Room, User, FeeType, PaymentMethod
from django.contrib.auth import get_user_model

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address')
    search_fields = ('name', 'address')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'building', 'capacity', 'gender_restriction')
    list_filter = ('building', 'gender_restriction')
    search_fields = ('name',)


User = get_user_model()


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = [field.name for field in User._meta.fields if field.name != 'password']
    exclude = ('password',)


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_recurring')
    search_fields = ('name',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'active')
    search_fields = ('name',)