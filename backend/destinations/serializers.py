from rest_framework import serializers

from .models import BeachVenue, Category, Destination, DestinationImage, MountainGuide


class DestinationImageSerializer(serializers.ModelSerializer):
    """Admin photo API. An uploaded file is NOT written to the server's disk:
    its bytes go into PostgreSQL (photostore.StoredPhoto), so photos survive
    restarts and redeploys on hosts with temporary disks (Render)."""

    src = serializers.CharField(read_only=True)
    credit_line = serializers.CharField(read_only=True)
    stored_in_database = serializers.SerializerMethodField()
    # Plain FileField (not the model's) so Django never saves it to MEDIA_ROOT.
    image_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = DestinationImage
        fields = ["id", "destination", "src", "image_file", "image_url", "caption", "credit", "license",
                  "source_page", "credit_line", "is_cover", "order", "stored_in_database"]
        extra_kwargs = {"image_url": {"required": False}}

    def get_stored_in_database(self, obj):
        return obj.image_url.startswith("/api/photos/")

    def validate_credit(self, v):
        if not v.strip():
            raise serializers.ValidationError("A photo credit is required.")
        return v

    def validate_image_url(self, v):
        # External links only (e.g. Wikimedia Commons). Database photos get their URL from the server.
        if v and not v.startswith("https://"):
            raise serializers.ValidationError("Use an https:// link, or upload the file instead.")
        return v

    def validate(self, attrs):
        if not self.instance and not attrs.get("image_file") and not attrs.get("image_url"):
            raise serializers.ValidationError("Upload a photo file or provide an image URL.")
        if attrs.get("image_file") and attrs.get("image_url"):
            raise serializers.ValidationError("Choose either a file upload or an image URL, not both.")
        return attrs

    def _user(self):
        req = self.context.get("request")
        return req.user if req and req.user.is_authenticated else None

    def create(self, validated):
        from photostore.services import make_cover, read_upload, store_new_photo

        f = validated.pop("image_file", None)
        if f:
            data, ctype = read_upload(f)
            return store_new_photo(data=data, content_type=ctype, original_name=f.name,
                                   uploaded_by=self._user(), **validated)
        image = super().create(validated)
        if image.is_cover:
            make_cover(image)
        return image

    def update(self, instance, validated):
        from photostore.services import make_cover, read_upload, replace_photo_bytes

        f = validated.pop("image_file", None)
        image = super().update(instance, validated)
        if f:
            data, ctype = read_upload(f)
            image = replace_photo_bytes(image, data=data, content_type=ctype, original_name=f.name,
                                        uploaded_by=self._user())
        if validated.get("is_cover"):
            make_cover(image)
        return image


class PublicVenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeachVenue
        fields = ["id", "name", "description", "max_guests", "base_price", "price_per_extra_guest",
                  "included_guests", "amenities", "is_demo"]


class PublicGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = MountainGuide
        fields = ["id", "display_name", "bio", "max_participants", "price_per_group", "price_per_participant",
                  "accreditation", "is_demo"]


class DestinationListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    is_bookable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Destination
        fields = ["id", "name", "slug", "category", "province", "municipality", "barangay", "location_verified",
                  "location_note", "short_description", "cover_image", "is_bookable", "is_featured", "is_verified"]

    def get_cover_image(self, obj):
        imgs = list(obj.images.all())  # prefetched
        if not imgs:
            return None
        img = next((i for i in imgs if i.is_cover), imgs[0])
        return {"url": img.src, "credit": img.credit_line, "caption": img.caption}


class DestinationDetailSerializer(DestinationListSerializer):
    images = DestinationImageSerializer(many=True, read_only=True)
    services = serializers.SerializerMethodField()

    class Meta(DestinationListSerializer.Meta):
        fields = DestinationListSerializer.Meta.fields + [
            "description", "amenities", "activities", "reservation_instructions", "latitude", "longitude",
            "images", "services", "booking_enabled",
        ]

    def get_services(self, obj):
        # Only verified, active, admin-configured services are ever shown.
        if obj.category == Category.BEACH:
            qs = obj.venues.filter(is_active=True, is_verified=True)
            return {"type": "VENUE", "items": PublicVenueSerializer(qs, many=True).data}
        qs = obj.guides.filter(is_active=True, is_verified=True)
        return {"type": "GUIDE", "items": PublicGuideSerializer(qs, many=True).data}


# ---------------- admin serializers ----------------
class AdminDestinationSerializer(serializers.ModelSerializer):
    is_bookable = serializers.BooleanField(read_only=True)
    cover_image = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()

    def get_cover_image(self, obj):
        return DestinationListSerializer.get_cover_image(self, obj)

    def get_photo_count(self, obj):
        return len(obj.images.all())  # prefetched

    class Meta:
        model = Destination
        fields = "__all__"
        read_only_fields = ["slug", "province", "created_at", "updated_at"]

    def validate(self, attrs):
        verified = attrs.get("is_verified", getattr(self.instance, "is_verified", False))
        enabled = attrs.get("booking_enabled", getattr(self.instance, "booking_enabled", False))
        if enabled and not verified:
            raise serializers.ValidationError("Verify the destination before enabling bookings.")
        for key in ("amenities", "activities"):
            if key in attrs and not (isinstance(attrs[key], list) and all(isinstance(x, str) for x in attrs[key])):
                raise serializers.ValidationError({key: "Must be a list of text items."})
        return attrs


class AdminVenueSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = BeachVenue
        fields = "__all__"

    def validate_destination(self, d):
        if d.category != Category.BEACH:
            raise serializers.ValidationError("Venues belong to beach destinations only.")
        return d


class AdminGuideSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = MountainGuide
        fields = "__all__"

    def validate_destination(self, d):
        if d.category != Category.MOUNTAIN:
            raise serializers.ValidationError("Tour guides belong to mountain destinations only.")
        return d
