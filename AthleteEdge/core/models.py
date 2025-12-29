from django.db import models
from django.core.exceptions import ValidationError
from django_userforeignkey.models.fields import UserForeignKey
from django.utils import timezone


class TimestampedModel(models.Model):

    def current_timestamp():
        return int(timezone.now().timestamp())

    created_at = models.IntegerField(default=current_timestamp, db_column="created_at")
    updated_at = models.IntegerField(default=current_timestamp, db_column="updated_at")
    updated_by = UserForeignKey(
        auto_user_add=True,
        on_delete=models.SET_NULL,
        db_column="updated_by",
        related_name="%(class)s_updated_by",
        null=True,
    )
    created_by = UserForeignKey(
        auto_user_add=True,
        on_delete=models.SET_NULL,
        db_column="created_by",
        related_name="%(class)s_created_by",
        null=True,
    )
    is_deleted = models.BooleanField(default=False, db_column="is_deleted", null=False)
    deleted_at = models.IntegerField(null=True, db_column="deleted_at", blank=True)
    deleted_by = UserForeignKey(
        auto_user_add=True,
        on_delete=models.SET_NULL,
        db_column="deleted_by",
        related_name="%(class)s_deleted_by",
        null=True,
    )
    detail = models.JSONField(null=True, db_column="detail")

    def clean(self):
        if (
            (self.created_at and int(self.created_at) < 0)
            or (self.updated_at and int(self.updated_at) < 0)
            or (self.deleted_at and int(self.deleted_at) < 0)
        ):
            raise ValidationError(
                ("Date Entries must be a positive interger or a date after 1970."),
                code="invalid",
            )

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = self.current_timestamp()
        if self.is_deleted and not self.deleted_at:
            self.deleted_at = self.current_timestamp()
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True