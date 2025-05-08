from django.utils import timezone

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, generics, status, parsers
from .models import User, Building, Room, RoomRegistration, RoomSwap, Invoice, InvoiceDetail
from . import serializers
from .perms import IsAdmin, OwnerPerms, RoomSwapOwner, IsStudent
from .utils.email import send_invoice_email
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
            return Response({"detail": f"{swap.desired_room.name} đã đầy."}, status=400)

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


class InvoiceViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView, generics.CreateAPIView):
    serializer_class = serializers.InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action.__eq__('pay'):
            return [IsAuthenticated(), IsStudent()]
        elif self.request.method.__eq__('POST'):
            return [IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if IsAdmin().has_permission(self.request, self):
            return Invoice.objects.all()
        elif IsStudent().has_permission(self.request, self):
            reg = RoomRegistration.objects.filter(student=user, is_active=True).first()
            if reg:
                return Invoice.objects.filter(room=reg.room)
        return Invoice.objects.none()

    def get_object(self):
        invoice = generics.get_object_or_404(Invoice, pk=self.kwargs.get('pk'))
        user = self.request.user
        if IsStudent().has_permission(self.request, self):
            reg = RoomRegistration.objects.filter(student=user, is_active=True).first()
            if not reg or reg.room != invoice.room:
                raise PermissionDenied("Hóa đơn không phải của phòng bạn!.")
        return invoice

    def get_serializer_class(self):
        if self.action == 'pay':
            return serializers.InvoicePaySerializer
        return serializers.InvoiceSerializer

    def perform_create(self, serializer):
        invoice = serializer.save()
        registrations = RoomRegistration.objects.filter(room=invoice.room, is_active=True)

        for reg in registrations:
            send_invoice_email(reg.student, invoice)

    @action(detail=True, methods=['patch'])
    def pay(self, request, pk=None):
        invoice = self.get_queryset().filter(pk=pk).first()
        if not invoice:
            return Response({"detail": "Không tìm thấy hóa đơn."}, status=404)

        if invoice.is_paid:
            return Response({"detail": "Hóa đơn đã thanh toán."}, status=400)

        # Check xem sinh viên có phải chủ phòng đang thuê không
        reg = RoomRegistration.objects.filter(student=request.user, is_active=True).first()
        if not reg or reg.room != invoice.room:
            return Response({"detail": "Bạn không có quyền thanh toán hóa đơn này."}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice.is_paid = True
        invoice.paid_at = timezone.now()
        invoice.payment_method = serializer.validated_data['payment_method']
        invoice.save()

        return Response({
            "message": "Thanh toán thành công.",
            "data": serializers.InvoiceSerializer(invoice).data
        }, status=200)


class InvoiceDetailViewSet(viewsets.GenericViewSet,
                           generics.ListAPIView,
                           generics.RetrieveAPIView,
                           generics.CreateAPIView):
    queryset = InvoiceDetail.objects.all()
    serializer_class = serializers.InvoiceDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
