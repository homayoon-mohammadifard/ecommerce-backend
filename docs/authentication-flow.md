# Authentication flow

Registration stores only a password hash in a pending OTP payload. A successful registration OTP consumes the OTP, creates a customer, and marks the phone verified atomically. Login returns Simple JWT access and refresh tokens. Logout validates refresh-token ownership before blacklisting it. Anonymous phone verification does not return another user's profile.
