from datetime import datetime
from django.conf import settings
from django.utils import timezone
from dormapis.dorms.models import Invoice
from dormapis.dorms.utils.vnpay import vnpay


class VNPayService:
    @staticmethod
    def create_payment_url(order_id, amount, order_desc, order_type, ip_address, language="vn", bank_code=None):
        vnp = vnpay()
        vnp.requestData = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': settings.VNPAY_TMN_CODE,
            'vnp_Amount': amount * 100,
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': order_id,
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': order_type,
            'vnp_Locale': language or 'vn',
            'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
            'vnp_IpAddr': ip_address,
            'vnp_ReturnUrl': settings.VNPAY_RETURN_URL,
        }
        if bank_code:
            vnp.requestData['vnp_BankCode'] = bank_code

        return vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)

    @staticmethod
    def handle_ipn(input_data: dict):
        vnp = vnpay()
        vnp.responseData = input_data
        order_id = input_data.get('vnp_TxnRef')
        response_code = input_data.get('vnp_ResponseCode')

        if not vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            return {'RspCode': '97', 'Message': 'Invalid Signature'}

        invoice_id = order_id.split("_")[0]
        invoice = Invoice.objects.filter(pk=invoice_id).first()
        if not invoice:
            return {'RspCode': '01', 'Message': 'Invoice not found'}

        if invoice.is_paid:
            return {'RspCode': '02', 'Message': 'Order Already Updated'}

        if response_code == '00':
            invoice.is_paid = True
            invoice.paid_at = timezone.now()
            invoice.payment_method = 'vnpay'
            invoice.save()

        return {'RspCode': '00', 'Message': 'Confirm Success'}
