from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('building', views.BuildingViewSet, basename='building')
router.register('room', views.RoomViewSet, basename='room')
urlpatterns = [
    path('', include(router.urls)),
]