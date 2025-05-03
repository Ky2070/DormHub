from django.utils import timezone

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, generics, status, parsers
from .models import User, Building, Room, RoomRegistration, RoomSwap
from . import serializers
from .perms import IsAdmin, OwnerPerms, RoomSwapOwner, IsStudent


# Create your views here.


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser, ]
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(methods=['get'], url_path='current-user', detail=False, permission_classes=[IsAuthenticated])
    def get_current_user(self, request):
        return Response(serializers.UserSerializer(request.user).data)

    @action(methods=['put', 'patch'], detail=True, url_path='update-profile', permission_classes=[OwnerPerms])
    def update_profile(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'Không tìm thấy người dùng.'}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, user)

        serializer = serializers.UpdateProfileSerializer(user, data=request.data,
                                                         partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Hồ sơ đã được cập nhật thành công."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Building.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.BuildingDetailSerializer
        return serializers.BuildingSerializer


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.select_related('building').all()
    serializer_class = serializers.RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        is_full = self.request.query_params.get('is_full')
        gender = self.request.query_params.get('gender_restriction')
        building_id = self.request.query_params.get('building_id')

        if is_full is not None:
            if is_full.lower() == 'false':
                queryset = [room for room in queryset if not room.is_full]
            elif is_full.lower() == 'true':
                queryset = [room for room in queryset if room.is_full]

        if gender:
            queryset = [room for room in queryset if room.gender_restriction == gender]

        if building_id:
            queryset = [room for room in queryset if str(room.building.id) == building_id]

        return queryset


class RoomRegisterViewSet(viewsets.ViewSet, generics.CreateAPIView):
    serializer_class = serializers.RegisterRoomSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class RoomSwapViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView):
    queryset = RoomSwap.objects.all()
    serializer_class = serializers.RoomSwapSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStudent()]
        elif self.request.method == 'GET':
            return [RoomSwapOwner()]
        return super().get_permissions()

    def get_queryset(self):
        # Trả về danh sách RoomSwap của student hiện tại, sắp xếp theo thời gian giảm dần
        return RoomSwap.objects.filter(student=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        student = self.request.user

        # Kiểm tra sinh viên đã có yêu cầu chuyển phòng chưa được duyệt chưa
        pending_swap = RoomSwap.objects.filter(student=student, is_approved=False).exists()
        if pending_swap:
            raise ValidationError("Bạn đã có yêu cầu chuyển phòng đang chờ xử lý.")

        # Kiểm tra sinh viên hiện có phòng không
        current_registration = student.roomregistration_set.filter(is_active=True).first()
        if not current_registration:
            raise ValidationError("Bạn chưa có phòng hiện tại để chuyển.")

        serializer.save(student=student, current_room=current_registration.room)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Gửi yêu cầu chuyển phòng thành công",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['put', 'patch'], url_path='approve', permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        """
        Admin PUT /room-swap/{id}/approve/ để duyệt yêu cầu chuyển phòng.
        """
        try:
            swap = self.get_object()
        except RoomSwap.DoesNotExist:
            return Response({"detail": "Yêu cầu không tồn tại."}, status=404)

        if swap.is_approved:
            return Response({"detail": "Yêu cầu này đã được duyệt."}, status=400)

        if swap.desired_room.is_full:
            return Response({"detail": f"Phòng {swap.desired_room.name} đã đầy."}, status=400)

        student = swap.student

        current_reg = RoomRegistration.objects.filter(student=student, is_active=True).first()
        if current_reg:
            current_reg.is_active = False
            current_reg.end_date = timezone.now().date()
            current_reg.save()

        RoomRegistration.objects.create(
            student=student,
            room=swap.desired_room,
            start_date=timezone.now().date()
        )

        swap.is_approved = True
        swap.processed_by = request.user
        swap.processed_at = timezone.now()
        swap.save()

        serializer = self.get_serializer(swap)
        return Response({
            "message": "Phê duyệt thành công",
            "data": serializer.data
        })

