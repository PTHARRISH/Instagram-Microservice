import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------- Base model ----------
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


# ---------- User ----------
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    display_name = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        indexes = [
            GinIndex(fields=["username"], name="user_username_gin"),
        ]


# ---------- Profile ----------
GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("nonbinary", "Non-binary"),
    ("other", "Other"),
    ("unset", "Unset"),
]


class Profile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE
    )
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default="unset")
    website = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    is_private = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_professional = models.BooleanField(default=False)

    links = models.JSONField(default=list, blank=True)

    posts = ArrayField(models.UUIDField(), default=list, blank=True)
    reels = ArrayField(models.UUIDField(), default=list, blank=True)
    stories = ArrayField(models.UUIDField(), default=list, blank=True)
    saved_posts = ArrayField(models.UUIDField(), default=list, blank=True)
    liked_posts = ArrayField(models.UUIDField(), default=list, blank=True)
    highlights = ArrayField(models.UUIDField(), default=list, blank=True)

    profile_views = models.BigIntegerField(default=0)

    class Meta:
        indexes = [
            GinIndex(fields=["bio"], name="profile_bio_gin"),
        ]


# ---------- Follow ----------
class Follow(BaseModel):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="following_rel", on_delete=models.CASCADE
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="followers_rel", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("follower", "following")
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]


# ---------- RBAC ----------
ACCESS_LEVEL_CHOICES = [
    ("NONE", "No Access"),
    ("VIEW", "View Only"),
    ("WRITE", "Write"),
    ("FULL", "Full"),
]


class Resource(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Permission(models.Model):
    resource = models.ForeignKey(
        Resource, related_name="permissions", on_delete=models.CASCADE
    )
    level = models.CharField(max_length=10, choices=ACCESS_LEVEL_CHOICES)

    class Meta:
        unique_together = ("resource", "level")

    def __str__(self):
        return f"{self.resource.name}:{self.level}"


class Role(BaseModel):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="user_roles", on_delete=models.CASCADE
    )
    role = models.ForeignKey(Role, related_name="user_roles", on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "role")
