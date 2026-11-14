from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from .models import Brand, Category, Product
from .serializers import BrandSerializer, CategorySerializer, ProductSerializer


class ManagerWritePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or bool(request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser or request.user.role == "manager"))


class PublicQuerysetMixin:
    permission_classes = [ManagerWritePermission]


class CategoryViewSet(PublicQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True)
    lookup_field = "slug"


class BrandViewSet(PublicQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    queryset = Brand.objects.filter(is_active=True)
    lookup_field = "slug"


class ProductViewSet(PublicQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.filter(is_active=True).select_related("category", "brand").prefetch_related("variants")
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "brand", "is_active"]
    search_fields = ["name", "description", "variants__sku"]
    ordering_fields = ["name", "created_at"]
