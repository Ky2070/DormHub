from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, generics, status, parsers
from .models import User
from . import serializers
from .perms import IsAdmin, OwnerPerms

from .serializers import UpdateProfileSerializer


# Create your views here.


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser, ]
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(methods=['get'], url_path='current-user', detail=False, permission_classes=[IsAuthenticated])
    def get_current_user(self, request):
        return Response(serializers.UserSerializer(request.user).data)

    @action(methods=['put'], detail=False, url_path='update-profile', permission_classes=[OwnerPerms])
    def update_profile(self, request):
        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data,
                                             partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Hồ sơ đã được cập nhật thành công."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
