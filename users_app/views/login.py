from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from users_app.serializers.login import LoginSerializer



class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer