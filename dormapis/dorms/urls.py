from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('building', views.BuildingViewSet, basename='building')
router.register('room', views.RoomViewSet, basename='room')
router.register('register-room', views.RoomRegisterViewSet, basename='register-room')
router.register('room-swap', views.RoomSwapViewSet, basename='swap-room')
router.register('invoice', views.InvoiceViewSet, basename='invoice')
router.register('invoice-detail', views.InvoiceDetailViewSet, basename='invoice-detail')
router.register('fcm',views.FCMTokenViewSet, basename='firebase-cloud-message')
urlpatterns = [
    path('', include(router.urls)),
    path('payment-return/', views.payment_return, name='payment_return'),
]