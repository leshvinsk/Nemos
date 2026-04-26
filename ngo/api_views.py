from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import filters, generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ngo.api_permissions import IsAdministratorUser, IsEmployeeUser
from ngo.models import NGO, NGOAvailability
from ngo.serializers import (
    ActivitySerializer,
    ActivityV2Serializer,
    NGOSerializer,
    RegistrationCreateSerializer,
    RegistrationSerializer,
)
from registrations.models import Registration
from registrations.services.registration_service import RegistrationService


class NGOListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = NGOSerializer
    permission_classes = [IsAuthenticated, IsAdministratorUser]
    queryset = NGO.objects.filter(is_active=True).order_by("name")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "contact_email"]
    ordering_fields = ["name", "created_at"]

    @extend_schema(
        summary="List NGOs",
        description="Administrator API for viewing active NGOs with pagination.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create NGO",
        description="Administrator API for creating a new NGO record.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class NGODetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NGOSerializer
    permission_classes = [IsAuthenticated, IsAdministratorUser]
    queryset = NGO.objects.filter(is_active=True).order_by("name")

    @extend_schema(summary="Retrieve NGO")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Update NGO")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(summary="Partially update NGO")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(summary="Deactivate NGO")
    def delete(self, request, *args, **kwargs):
        ngo = self.get_object()
        ngo.is_active = False
        ngo.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityListAPIView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated, IsEmployeeUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["location", "service_type"]
    ordering_fields = ["service_date", "cutoff_time", "location"]
    ordering = ["service_date"]

    def get_queryset(self):
        queryset = (
            NGOAvailability.objects.select_related("ngo")
            .filter(is_active=True, ngo__is_active=True)
            .annotate(registration_count=Count("registrations"))
            .order_by("service_date", "ngo__name")
        )

        service_date_from = self.request.query_params.get("service_date_from")
        if service_date_from:
            parsed = parse_datetime(service_date_from)
            if parsed is None:
                raise serializers.ValidationError(
                    {"service_date_from": "Use ISO datetime format such as 2026-04-30T09:00:00Z."}
                )
            queryset = queryset.filter(service_date__gte=parsed)

        return queryset

    @extend_schema(
        summary="List activities",
        description="Employee API for listing available activities with pagination and filtering.",
        parameters=[
            OpenApiParameter(
                name="location",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by activity location.",
            ),
            OpenApiParameter(
                name="service_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by service type.",
            ),
            OpenApiParameter(
                name="service_date_from",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter activities on or after the given ISO datetime.",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ActivityListV2APIView(generics.ListAPIView):
    serializer_class = ActivityV2Serializer
    permission_classes = [IsAuthenticated, IsEmployeeUser]
    queryset = NGOAvailability.objects.select_related("ngo").filter(
        is_active=True,
        ngo__is_active=True,
    ).order_by("service_date", "ngo__name")

    @extend_schema(summary="List activities v2")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class RegistrationCreateAPIView(generics.CreateAPIView):
    serializer_class = RegistrationCreateSerializer
    permission_classes = [IsAuthenticated, IsEmployeeUser]

    @extend_schema(
        summary="Register for an activity",
        examples=[
            OpenApiExample(
                "Registration request",
                value={"activity_id": 1},
                request_only=True,
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        output = RegistrationSerializer(registration)
        return Response(output.data, status=status.HTTP_201_CREATED)


class RegistrationCancelAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeUser]

    @extend_schema(summary="Cancel a registration")
    def delete(self, request, activity_id):
        success, message = RegistrationService.cancel_registration(request.user, activity_id)
        if not success:
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": message}, status=status.HTTP_200_OK)


class RegistrationListAPIView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated, IsEmployeeUser]

    def get_queryset(self):
        return Registration.objects.filter(employee=self.request.user).select_related(
            "activity__ngo",
            "employee",
        )
