class AuthServiceError(Exception):
    status_code = 400
    default_message = "درخواست نامعتبر است."
    code = "invalid"

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidOtp(AuthServiceError):
    default_message = "کد تأیید نامعتبر است."
    code = "invalid_otp"


class RateLimited(AuthServiceError):
    status_code = 429
    default_message = "تعداد تلاش‌ها بیش از حد مجاز است. لطفاً بعداً دوباره تلاش کنید."
    code = "rate_limited"


class InvalidCredentials(AuthServiceError):
    default_message = "شماره موبایل یا رمز عبور نادرست است."
    code = "invalid_credentials"


class SmsDeliveryError(AuthServiceError):
    default_message = 'ارسال کد تأیید انجام نشد. لطفاً دوباره تلاش کنید.'
    code = 'sms_delivery_failed'

class DatabaseConflict(AuthServiceError):
    status_code = 409
    default_message = 'اطلاعات تکراری است.'
    code = 'conflict'
