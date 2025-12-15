import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.models import Follow, Profile, Role, User, UserRole


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "display_name",
            "role",
            "mobile_number",
        ]

    def validate_username(self, value):
        if len(value) < 4:
            raise serializers.ValidationError("Username must be at least 4 characters.")

        if not re.match(r"^[A-Za-z][A-Za-z0-9_.]*$", value):
            raise serializers.ValidationError(
                "Username must start with a letter and contain only letters, numbers, _ or ."
            )

        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")

        return value

    def validate_mobile_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Mobile number must contain only digits")

        if len(value) < 10:
            raise serializers.ValidationError("Invalid mobile number")

        if User.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError("Mobile number already registered")

        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")

        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                "Password must contain an uppercase letter."
            )
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError(
                "Password must contain a lowercase letter."
            )
        if not re.search(r"\d", value):
            raise serializers.ValidationError("Password must contain a number.")
        if not re.search(r"[^\w\s]", value):
            raise serializers.ValidationError("Password must contain a symbol.")

        validate_password(value)
        return value

    def create(self, validated_data):
        role_name = validated_data.pop("role", "user")

        user = User.objects.create_user(**validated_data)

        Profile.objects.create(user=user)

        # assign role
        role, _ = Role.objects.get_or_create(name=role_name.upper())
        UserRole.objects.create(user=user, role=role)

        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False, required=False)

    def validate_identifier(self, value):
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError("Invalid login identifier")

        return value


class ProfileSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        exclude = ["id"]
        read_only_fields = ["user", "profile_views"]

    def get_followers_count(self, obj):
        return Follow.objects.filter(following=obj.user).count()

    def get_following_count(self, obj):
        return Follow.objects.filter(follower=obj.user).count()

    def to_representation(self, instance):
        """
        Privacy enforcement:
        If profile is private → only followers can view
        """
        request = self.context.get("request")
        if not request:
            return super().to_representation(instance)

        viewer = request.user

        if instance.is_private:
            if viewer != instance.user:
                is_follower = Follow.objects.filter(
                    follower=viewer, following=instance.user
                ).exists()

                if not is_follower:
                    return {
                        "detail": "This profile is private. Follow to view details."
                    }

        return super().to_representation(instance)
