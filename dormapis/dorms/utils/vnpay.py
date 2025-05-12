# utils/vnpay.py
import hashlib
import hmac
import urllib.parse


class vnpay:
    def __init__(self):
        self.requestData = {}
        self.responseData = {}

    def get_payment_url(self, base_url, hash_secret):
        query = self._build_query(self.requestData)
        hash_value = self._hmac_sha512(hash_secret, query)
        payment_url = f"{base_url}?{query}&vnp_SecureHash={hash_value}"
        return payment_url

    def validate_response(self, hash_secret):
        response = self.responseData.copy()
        secure_hash = response.pop('vnp_SecureHash', None)
        response.pop('vnp_SecureHashType', None)
        sorted_query = self._build_query(response)
        expected_hash = self._hmac_sha512(hash_secret, sorted_query)
        return secure_hash == expected_hash

    def _build_query(self, data):
        sorted_data = sorted(data.items())
        return urllib.parse.urlencode(sorted_data)

    def _hmac_sha512(self, key, data):
        byte_key = bytes(key, 'utf-8')
        message = bytes(data, 'utf-8')
        return hmac.new(byte_key, message, hashlib.sha512).hexdigest()
