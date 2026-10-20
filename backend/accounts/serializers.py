from django.contrib.auth import password_validation
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[User.Role.TOURIST, User.Role.BUSINESS], default=User.Role.TOURIST)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "first_name", "last_name", "role", "language")

    def validate(self, attrs):
        password_validation.validate_password(attrs["password"], User(**{k: v for k, v in attrs.items() if k != "password"}))
        return attrs

    def create(self, validated):
        password = validated.pop("password")
        user = User(**validated)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name", "role", "bio", "avatar",
            "language", "preferences", "is_profile_public", "favorite_places",
        )
        read_only_fields = ("id", "username", "role")


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "avatar")
