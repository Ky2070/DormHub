from datetime import datetime

from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from .utils.vnpay import VNPay
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, generics, status, parsers
from .models import User, Building, Room, RoomRegistration, RoomSwap, Invoice, InvoiceDetail, FCMDevice, SupportRequest, \
    Notification
from . import serializers, paginators
from .perms import IsAdmin, OwnerPerms, RoomSwapOwner, IsStudent
from .services.vnpay_service import VNPayService
from .services import firebase_service
from .utils.email import send_invoice_email, send_invoice_payment_success_email


# Create your views here.


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser, ]
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(methods=['get'], url_path='current-user', detail=False, permission_classes=[IsAuthenticated])
    def get_current_user(self, request):
        serializer = serializers.UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

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

    @action(methods=['get'], detail=False, url_path='my-room', permission_classes=[IsAuthenticated])
    def my_room(self, request):
        try:
            registration = RoomRegistration.objects.select_related('room', 'room__building') \
                .get(student=request.user, is_active=True)
            room = registration.room
            serializer = serializers.RoomSerializer(room, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except RoomRegistration.DoesNotExist:
            return Response({"detail": "Bạn chưa ở phòng nào hiện tại."}, status=status.HTTP_404_NOT_FOUND)


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Building.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.BuildingDetailSerializer
        return serializers.BuildingSerializer


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.select_related('building').all().order_by('id')
    serializer_class = serializers.RoomSerializer
    pagination_class = paginators.ItemPaginator

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


class RoomRegisterViewSet(viewsets.ViewSet,
                          generics.CreateAPIView):
    queryset = RoomRegistration.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStudent()]
        elif self.request.method == 'GET':
            return [IsAdmin()]
        return [IsAuthenticated()]  # fallback

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.RoomRegistrationAdminSerializer
        return serializers.RegisterRoomSerializer

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def list(self, request):
        if not IsAdmin().has_permission(request, self):
            raise PermissionDenied("Chỉ quản trị viên mới được xem danh sách đăng ký phòng.")

        queryset = RoomRegistration.objects.select_related('student', 'room', 'room__building')
        serializer = serializers.RoomRegistrationAdminSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

            # Validate payment_method thông qua serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment_method = serializer.validated_data['payment_method']

        amount = int(invoice.total_amount)  # từ property tính từ InvoiceDetail
        order_id = f"{invoice.id}_{int(datetime.now().timestamp())}"
        order_desc = f"Hóa đơn ký túc xá tháng {invoice.billing_period.strftime('%m/%Y')}"
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')

        payment_url = VNPayService.create_payment_url(
            order_id=order_id,
            amount=amount,
            order_desc=order_desc,
            order_type="billpayment",
            ip_address=ip,
        )

        # Optional: lưu payment_method tạm vào invoice để sau IPN update
        invoice.payment_method = payment_method
        invoice.save(update_fields=['payment_method'])

        return Response({
            "payment_url": payment_url,
            "amount": amount
        }, status=200)


class InvoiceDetailViewSet(viewsets.GenericViewSet,
                           generics.ListAPIView,
                           generics.RetrieveAPIView,
                           generics.CreateAPIView):
    queryset = InvoiceDetail.objects.all()
    serializer_class = serializers.InvoiceDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def perform_create(self, serializer):
        detail = serializer.save()
        invoice = detail.invoice

        # Danh sách loại phí (có thể tùy chỉnh nếu có thay đổi về gói dịch vụ)
        required_fee_types = {'Tiền phòng', 'Điện', 'Nước', 'Internet'}

        existing_fee_types = set(invoice.invoice_details.values_list('fee_type__name', flat=True))

        if required_fee_types.issubset(existing_fee_types):
            registrations = RoomRegistration.objects.filter(room=invoice.room, is_active=True)
            for reg in registrations:
                send_invoice_email(reg.student, invoice)

            # Gửi thông báo
            firebase_service.notify_user(
                user=invoice.student,
                title="Hóa đơn mới",
                body=f"Hóa đơn {invoice.code} đã được tạo, tổng tiền: {invoice.total_amount} VNĐ",
                data={
                    "invoice_id": str(invoice.id),
                    "type": "new_invoice"
                }
            )


def payment_return(request):
    input_data = request.GET.dict()
    vnp = VNPay()
    vnp.responseData = input_data

    # Kiểm tra chữ ký của dữ liệu trả về
    if not vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
        return JsonResponse({"RspCode": "97", "Message": "Invalid Signature"}, status=400)

    # Lấy mã giao dịch (TxnRef) từ dữ liệu trả về
    order_id = input_data.get('vnp_TxnRef')
    response_code = input_data.get('vnp_ResponseCode')

    # Tìm hóa đơn dựa trên mã giao dịch (TxnRef)
    invoice_id = order_id.split("_")[0]
    invoice = Invoice.objects.filter(pk=invoice_id).first()

    if not invoice:
        return JsonResponse({"RspCode": "01", "Message": "Invoice not found"}, status=404)

    # Nếu hóa đơn đã được thanh toán rồi
    if invoice.is_paid:
        return JsonResponse({"RspCode": "02", "Message": "Order already updated"}, status=400)

    # Kiểm tra mã phản hồi từ VNPay, "00" là thanh toán thành công

    if response_code == "00":
        invoice.is_paid = True
        invoice.paid_at = timezone.now()
        invoice.save()

        registrations = RoomRegistration.objects.filter(room=invoice.room, is_active=True)
        for reg in registrations:
            send_invoice_payment_success_email(reg.student, invoice)

        firebase_service.notify_user(
            user=invoice.student,
            title="Thanh toán thành công",
            body=f"Hóa đơn {invoice.code} đã được thanh toán thành công.",
            data={
                "invoice_id": str(invoice.id),
                "type": "invoice_paid"
            }
        )

        return JsonResponse({
            "RspCode": "00",
            "Message": "Confirm Success",
            "invoice_data": {
                "invoice_id": invoice.id,
                "amount": invoice.total_amount,
                "status": "Paid",
                "paid_at": invoice.paid_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        })

    return JsonResponse({
        "RspCode": "02",
        "Message": "Payment failed",
        "Invoice": {
            "invoice_id": invoice.id,
            "amount": invoice.total_amount,
            "status": "Failed"
        }
    }, status=400)


class FCMTokenViewSet(viewsets.ViewSet, generics.CreateAPIView):
    serializer_class = serializers.FCMDeviceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        token = serializer.validated_data['token']
        FCMDevice.objects.update_or_create(
            user=self.request.user,
            token=token,
            defaults={'token': token}
        )


class NotificationViewSet(viewsets.GenericViewSet,
                          generics.ListAPIView,
                          generics.CreateAPIView):
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = serializers.NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Notification.objects.all()
        return Notification.objects.filter(target_users=user)

    # def perform_create(self, serializer):
    #     notif = serializer.save(sent_by=self.request.user)
    #
    #     # Gửi FCM cho từng user
    #     for user in notif.target_users.all():
    #         firebase_service.notify_user(
    #             user=user,
    #             title=notif.title,
    #             body=notif.content,
    #             data={
    #                 "type": "notification",
    #                 "notification_id": notif.id
    #             },
    #             is_urgent=notif.is_urgent
    #         )


class SupportRequestViewSet(viewsets.GenericViewSet,
                            generics.ListAPIView,
                            generics.CreateAPIView):
    serializer_class = serializers.SupportRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return SupportRequest.objects.all().order_by('-created_at')
        return SupportRequest.objects.filter(student=user).order_by('-created_at')

    def perform_create(self, serializer):
        # Auto-đính kèm phòng của sinh viên nếu chưa có
        room = serializer.validated_data.get('room') or getattr(self.request.user, 'room', None)
        serializer.save(student=self.request.user, room=room)


class SupportResponseViewSet(viewsets.GenericViewSet,
                             generics.CreateAPIView):
    serializer_class = serializers.SupportResponseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def perform_create(self, serializer):
        response = serializer.save(responder=self.request.user)

        # Gửi FCM cho sinh viên khi có phản hồi
        firebase_service.notify_user(
            user=response.request.student,
            title="Phản hồi yêu cầu hỗ trợ",
            body=f"Yêu cầu '{response.request.title}' đã được phản hồi.",
            data={
                "type": "support_response",
                "request_id": response.request.id
            }
        )