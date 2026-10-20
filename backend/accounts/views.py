from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import MeSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"


class LoginView(TokenObtainPairView):
    throttle_scope = "login"


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
