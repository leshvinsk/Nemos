from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from ngo.models import NGO, NGOAvailability
from registrations.models import Registration


class NGOSerializer(serializers.ModelSerializer):
    class Meta:
        model = NGO
        fields = [
            "id",
            "name",
            "description",
            "contact_email",
            "contact_phone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ActivitySerializer(serializers.ModelSerializer):
    ngo_name = serializers.CharField(source="ngo.name", read_only=True)
    slots_taken = serializers.SerializerMethodField()
    slots_remaining = serializers.SerializerMethodField()

    class Meta:
        model = NGOAvailability
        fields = [
            "id",
            "ngo",
            "ngo_name",
            "service_type",
            "description",
            "location",
            "service_date",
            "cutoff_time",
            "max_slots",
            "is_active",
            "slots_taken",
            "slots_remaining",
        ]

    def get_slots_taken(self, obj):
        annotated = getattr(obj, "registration_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.registrations.count()

    def get_slots_remaining(self, obj):
        taken = self.get_slots_taken(obj)
        return max(int(obj.max_slots) - taken, 0)


class ActivityV2Serializer(serializers.ModelSerializer):
    ngo = serializers.CharField(source="ngo.name", read_only=True)

    class Meta:
        model = NGOAvailability
        fields = ["id", "ngo", "service_type", "location", "service_date"]


class RegistrationSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="employee.username", read_only=True)
    activity_name = serializers.CharField(source="activity.ngo.name", read_only=True)

    class Meta:
        model = Registration
        fields = [
            "id",
            "employee",
            "employee_username",
            "activity",
            "activity_name",
            "registered_at",
        ]
        read_only_fields = ["id", "employee", "employee_username", "activity_name", "registered_at"]


class RegistrationCreateSerializer(serializers.Serializer):
    activity_id = serializers.IntegerField()

    def validate_activity_id(self, value):
        try:
            activity = NGOAvailability.objects.select_related("ngo").get(
                id=value,
                is_active=True,
                ngo__is_active=True,
            )
        except NGOAvailability.DoesNotExist as exc:
            raise serializers.ValidationError("Activity not found or inactive.") from exc

        if timezone.now() > activity.cutoff_time:
            raise serializers.ValidationError("Registration cutoff time has passed.")

        self.context["activity"] = activity
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        activity = self.context["activity"]

        if Registration.objects.filter(employee=user, activity=activity).exists():
            raise serializers.ValidationError({"activity_id": "You are already registered for this activity."})

        taken = Registration.objects.filter(activity=activity).count()
        if taken >= activity.max_slots:
            raise serializers.ValidationError({"activity_id": "No slots remaining for this activity."})

        return attrs

    def create(self, validated_data):
        registration = Registration(
            employee=self.context["request"].user,
            activity=self.context["activity"],
        )
        try:
            registration.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        registration.save()
        return registration
