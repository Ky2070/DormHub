from django.contrib import admin
from .models import (
    Building, Room, RoomRegistration, RoomSwap,
    FeeType, PaymentMethod, Invoice, InvoiceDetail,
    NotificationType, Notification, FCMDevice,
    SupportRequest, SupportResponse,
    Survey, SurveyQuestion, SurveyResponse
)
from django.utils.html import mark_safe
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib.auth import get_user_model
from django.utils.html import format_html


class MyAdminSite(admin.AdminSite):
    site_header = 'OU Dorms Online'


admin_site = MyAdminSite(name='admin')


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address')
    search_fields = ('name', 'address')


class RoomForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Room
        fields = '__all__'


class MyRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'building', 'image_tag', 'capacity', 'gender_restriction')
    list_filter = ('building', 'gender_restriction')
    search_fields = ('name',)
    readonly_fields = ['image_view']
    form = RoomForm

    def image_tag(self, obj):
        if obj.image:
            return format_html(f'<img src="{obj.image.url}" width="100" height="auto" style="object-fit: cover;" />', obj.image.url)
        return "-"

    image_tag.short_description = 'Image'  # Cột tiêu đề

    def image_view(self, rooms):
        if rooms:
            return mark_safe(f"<img src='{rooms.image.url}' width='120' />")


admin.site.register(Room, MyRoomAdmin)


User = get_user_model()


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'student_code', 'phone', 'role', 'gender')
    exclude = ('password',)
    search_fields = ('username', 'email', 'first_name', 'last_name', 'student_code', 'phone')


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_recurring')
    search_fields = ('name',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'active')
    search_fields = ('name',)


@admin.register(RoomRegistration)
class RoomRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'registered_at', 'start_date', 'end_date', 'is_active')
    search_fields = ('student__username', 'room__name')
    list_filter = ('is_active', 'room__building')
    autocomplete_fields = ('student', 'room')


class InvoiceDetailInline(admin.TabularInline):
    model = InvoiceDetail
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('room', 'billing_period', 'is_paid', 'paid_at', 'payment_method', 'total_amount')
    list_filter = ('is_paid', 'room__building')
    search_fields = ('room__name',)
    inlines = [InvoiceDetailInline]


@admin.register(InvoiceDetail)
class InvoiceDetailAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'fee_type', 'quantity', 'unit', 'unit_price', 'amount')
    search_fields = ('invoice__room__name', 'fee_type__name')
    list_filter = ('unit',)


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'created_at', 'sent_by', 'is_urgent')
    search_fields = ('title', 'content')
    list_filter = ('notification_type', 'is_urgent')
    filter_horizontal = ('target_users',)


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'room', 'created_at', 'is_resolved')
    search_fields = ('title', 'student__username')
    list_filter = ('is_resolved',)


@admin.register(SupportResponse)
class SupportResponseAdmin(admin.ModelAdmin):
    list_display = ('request', 'responder', 'responded_at')
    search_fields = ('request__title', 'responder__username')


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'start_date', 'end_date')
    search_fields = ('title',)
    list_filter = ('start_date', 'end_date')


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'survey')


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'answer')
    search_fields = ('student__username', 'question__question_text')


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at')
    search_fields = ('user__username', 'token')


