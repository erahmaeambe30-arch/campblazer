from django.contrib import admin

from .models import StoredPhoto


@admin.register(StoredPhoto)
class StoredPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "image", "content_type", "size_bytes", "uploaded_by", "created_at")
    readonly_fields = ("id", "image", "content_type", "size_bytes", "sha256", "original_name", "uploaded_by",
                       "created_at")
    exclude = ("data",)

    def has_add_permission(self, request):
        return False  # upload through the CampBlazer admin dashboard
