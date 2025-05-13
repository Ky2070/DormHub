from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta


def send_invoice_email(user, invoice):
    due_date = invoice.billing_period + timedelta(days=7)
    formatted_due_date = due_date.strftime('%d/%m/%Y')
    total_amount = sum([detail.amount or 0 for detail in invoice.invoice_details.all()])
    formatted_amount = "{:,.0f} VND".format(total_amount)
    subject = f"Hóa đơn tiền phòng {invoice.billing_period.strftime('%d/%m/%Y')} từ ký túc xá"
    message = f"""
        Xin chào {user.last_name},
        Bạn có hóa đơn mới cho {invoice.room.name}.
        Tổng tiền cần thanh toán: {formatted_amount}
        Hạn thanh toán: {formatted_due_date}

        Vui lòng đăng nhập hệ thống để xem chi tiết và thanh toán.

        Trân trọng,
        Ban quản lý ký túc xá
        """
    recipient = [user.email]
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient)


def send_invoice_payment_success_email(user, invoice):
    # Tạo nội dung email thông báo thanh toán thành công
    formatted_amount = "{:,.0f} VND".format(invoice.total_amount)
    formatted_paid_at = invoice.paid_at.strftime('%d/%m/%Y %H:%M:%S')

    subject = f"Thông báo thanh toán hóa đơn ký túc xá - Tháng {invoice.billing_period.strftime('%m/%Y')}"
    message = f"""
        Xin chào {user.first_name} {user.last_name},

        Hóa đơn tiền phòng cho {invoice.room.name} của bạn đã được thanh toán thành công.

        Chi tiết thanh toán:
        - Mã hóa đơn: {invoice.id}
        - Tổng tiền: {formatted_amount}
        - Ngày thanh toán: {formatted_paid_at}

        Cảm ơn bạn đã sử dụng dịch vụ của ký túc xá!

        Trân trọng,
        Ban quản lý ký túc xá
    """
    recipient = [user.email]
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient)