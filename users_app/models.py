import random
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from shared_app.models import BaseModel

ORDINARY_USER, ADMIN, MANAGER = ('ordinary_user', 'admin', 'manager')
VIA_EMAIL, VIA_PHONE = ('email', 'phone')
NEW, CONFIRMED, DONE, IMAGE_STEP = ('new', 'confirmed', 'done', 'photo_step')


class User(AbstractUser, BaseModel):
    USER_ROLES = (
        (ORDINARY_USER, ORDINARY_USER),
        (ADMIN, ADMIN),
        (MANAGER, MANAGER)
    )

    AUTH_TYPES = (
        (VIA_EMAIL, VIA_EMAIL),
        (VIA_PHONE, VIA_PHONE)
    )

    AUTH_STATUS = (
        (NEW, NEW),
        (CONFIRMED, CONFIRMED),
        (DONE, DONE),
        (IMAGE_STEP, IMAGE_STEP)
    )
    phone_number = models.CharField(max_length=13, null=True, blank=True, unique=True)
    email = models.EmailField(null=True, blank=True, unique=True)
    user_role = models.CharField(max_length=31, choices=USER_ROLES, default=ORDINARY_USER)
    auth_type = models.CharField(max_length=50, choices=AUTH_TYPES)
    auth_status = models.CharField(max_length=31, choices=AUTH_STATUS, default=NEW)
    image = models.ImageField(null=True, blank=True, upload_to="users_images"
                              , validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "heic"])])

    def __str__(self):
        return self.username

    @property
    def get_fullname(self):
        return f"{self.first_name} {self.last_name}"

    def create_verify_code(self, verify_type):
        code = "".join([str(random.randint(0, 100) % 10) for _ in range(4)])
        UserConfirmation.objects.create(
            user_id=self.id,
            verify_type=verify_type,
            code=code
        )
        return code

    def check_username(self):
        if not self.username:
            temp_username = f"instagram-{uuid.uuid4().__str__().split('-')[-1]}"
            while User.objects.filter(username=temp_username).exists():
                temp_username = f"{temp_username}{random.randint(0, 9)}"
            self.username = temp_username

    def check_email(self):
        if self.email:
            normalize_email = self.email.lower()
            self.email = normalize_email

    def ensure_password(self):
        if not self.password:
            temp_password = f"password-{uuid.uuid4().__str__().split('-')[-1]}"
            self.password = temp_password

    def hashing_password(self):
        if not self.password.startswith("pbkdf2_sha256"):
            self.set_password(self.password)

    def token(self):
        refresh = RefreshToken.for_user(self)
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }

    def clean(self):
        self.check_username()
        self.check_email()
        self.ensure_password()
        self.hashing_password()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


EMAIL_EXPIRE = 2
PHONE_NUMBER_EXPIRE = 3


class UserConfirmation(BaseModel):
    TYPE_CHOICES = (
        (VIA_PHONE, VIA_PHONE),
        (VIA_EMAIL, VIA_EMAIL),
    )
    code = models.CharField(max_length=4)
    verify_type = models.CharField(max_length=31, choices=TYPE_CHOICES)
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE, related_name='user_confirmations')
    expiration_time = models.DateTimeField(null=True)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user.__str__())

    def save(self, *args, **kwargs):
        if self.verify_type == VIA_EMAIL:
            self.expiration_time = timezone.now() + timedelta(minutes=EMAIL_EXPIRE)
        elif self.verify_type == VIA_PHONE:
            self.expiration_time = timezone.now() + timedelta(minutes=PHONE_NUMBER_EXPIRE)

        super(UserConfirmation, self).save(*args, **kwargs)
