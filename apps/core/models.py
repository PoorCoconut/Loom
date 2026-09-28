from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """Bulk deletes flag rows instead of removing them (also covers admin's bulk-delete)."""

    def delete(self):
        count = self.update(is_deleted=True)
        return count, {self.model._meta.label: count}

    def hard_delete(self):
        return super().delete()


class AliveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: never returns soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """Adds the ERD's `is_deleted` flag.

    Model.objects      -> only live rows
    Model.all_objects  -> everything, including soft-deleted rows
    """

    is_deleted = models.BooleanField(default=False)

    objects = AliveManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])
        return 1, {self._meta.label: 1}

    def restore(self):
        self.is_deleted = False
        self.save(update_fields=["is_deleted"])

    def hard_delete(self):
        return super().delete()
