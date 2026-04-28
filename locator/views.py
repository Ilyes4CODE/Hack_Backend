from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from Auth.permissions import IsFarmer
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import AidCenter
from .utils import sort_centers_by_distance

# ─── Swagger Parameters & Schemas ───
lat_param = openapi.Parameter('lat', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=True)
lon_param = openapi.Parameter('lon', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=True)
limit_param = openapi.Parameter('limit', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False)
type_param = openapi.Parameter('type', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, enum=['chamber', 'cooperative', 'itdas'])
wilaya_param = openapi.Parameter('wilaya', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False)

center_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'name': openapi.Schema(type=openapi.TYPE_STRING),
        'type': openapi.Schema(type=openapi.TYPE_STRING),
        'wilaya': openapi.Schema(type=openapi.TYPE_STRING),
        'address': openapi.Schema(type=openapi.TYPE_STRING),
        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
        'phone': openapi.Schema(type=openapi.TYPE_STRING),
        'email': openapi.Schema(type=openapi.TYPE_STRING),
        'distance_km': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
    }
)

center_create_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['name', 'center_type', 'wilaya', 'latitude', 'longitude'],
    properties={
        'name': openapi.Schema(type=openapi.TYPE_STRING),
        'center_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['chamber', 'cooperative', 'itdas']),
        'wilaya': openapi.Schema(type=openapi.TYPE_STRING),
        'address': openapi.Schema(type=openapi.TYPE_STRING),
        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
        'phone': openapi.Schema(type=openapi.TYPE_STRING),
        'email': openapi.Schema(type=openapi.TYPE_STRING),
    }
)

center_patch_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'name': openapi.Schema(type=openapi.TYPE_STRING),
        'center_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['chamber', 'cooperative', 'itdas']),
        'wilaya': openapi.Schema(type=openapi.TYPE_STRING),
        'address': openapi.Schema(type=openapi.TYPE_STRING),
        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
        'phone': openapi.Schema(type=openapi.TYPE_STRING),
        'email': openapi.Schema(type=openapi.TYPE_STRING),
        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
    }
)

# ─── Views ───
class NearestCentersView(APIView):
    """Fetches centers sorted by distance from user's GPS. Ideal for "single-tap" map load."""
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Get nearest aid centers",
        operation_description="Returns active centers sorted by proximity to the farmer's current location. No manual city entry needed.",
        manual_parameters=[lat_param, lon_param, limit_param, type_param],
        responses={
            200: openapi.Response('List of nearest centers', openapi.Schema(type=openapi.TYPE_ARRAY, items=center_response)),
            400: 'Invalid or missing lat/lon parameters',
            401: 'Authentication required',
        },
        security=[{"Bearer": []}], tags=['Locator']
    )
    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except (TypeError, ValueError):
            return Response({'error': 'Valid lat and lon are required.'}, status=status.HTTP_400_BAD_REQUEST)

        limit = int(request.query_params.get('limit', 10))
        qs = AidCenter.objects.filter(is_active=True)
        if request.query_params.get('type'):
            qs = qs.filter(center_type=request.query_params['type'])

        ranked = sort_centers_by_distance(list(qs), lat, lon)[:limit]
        return Response([{
            'id': c.id, 'name': c.name, 'type': c.center_type, 'wilaya': c.wilaya,
            'address': c.address, 'latitude': c.latitude, 'longitude': c.longitude,
            'phone': c.phone, 'email': c.email, 'distance_km': dist
        } for c, dist in ranked], status=status.HTTP_200_OK)


class CenterListView(APIView):
    """Shows ALL active centers for the full map view."""
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="List all active aid centers",
        operation_description="Returns every active agricultural center submitted by farmers. Used to populate the regional map. Filterable by wilaya and type.",
        manual_parameters=[wilaya_param, type_param],
        responses={
            200: openapi.Response('Centers list', openapi.Schema(type=openapi.TYPE_ARRAY, items=center_response)),
            401: 'Authentication required',
        },
        security=[{"Bearer": []}], tags=['Locator']
    )
    def get(self, request):
        # ✅ REMOVED created_by=request.user so farmers see EVERYONE'S centers
        qs = AidCenter.objects.filter(is_active=True)
        
        if request.query_params.get('wilaya'):
            qs = qs.filter(wilaya__icontains=request.query_params['wilaya'])
        if request.query_params.get('type'):
            qs = qs.filter(center_type=request.query_params['type'])

        return Response([{
            'id': c.id, 'name': c.name, 'type': c.center_type, 'wilaya': c.wilaya,
            'address': c.address, 'latitude': c.latitude, 'longitude': c.longitude,
            'phone': c.phone, 'email': c.email, 'is_active': c.is_active
        } for c in qs], status=status.HTTP_200_OK)


class CenterCreateView(APIView):
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Register a new aid center",
        operation_description="Farmers can add their chamber, cooperative, or ITDAS center to the community map.",
        request_body=center_create_body,
        responses={201: 'Center created', 400: 'Validation error', 401: 'Unauthorized'},
        security=[{"Bearer": []}], tags=['Locator']
    )
    def post(self, request):
        required = ['name', 'center_type', 'wilaya', 'latitude', 'longitude']
        for field in required:
            if not request.data.get(field):
                return Response({'error': f'{field} is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat, lon = float(request.data['latitude']), float(request.data['longitude'])
        except ValueError:
            return Response({'error': 'Latitude and longitude must be valid numbers.'}, status=status.HTTP_400_BAD_REQUEST)

        center = AidCenter.objects.create(
            name=request.data['name'],
            center_type=request.data['center_type'],
            wilaya=request.data['wilaya'],
            address=request.data.get('address', ''),
            latitude=lat,
            longitude=lon,
            phone=request.data.get('phone', ''),
            email=request.data.get('email', ''),
            created_by=request.user,  # ✅ Ownership tracked but not restricted from public view
        )
        return Response({'id': center.id, 'message': 'Center added to the map.'}, status=status.HTTP_201_CREATED)


class CenterDetailView(APIView):
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Get center details",
        responses={200: center_response, 404: 'Not found'},
        security=[{"Bearer": []}], tags=['Locator']
    )
    def get(self, request, pk):
        center = get_object_or_404(AidCenter, pk=pk, is_active=True)
        return Response({
            'id': center.id, 'name': center.name, 'type': center.center_type,
            'wilaya': center.wilaya, 'address': center.address,
            'latitude': center.latitude, 'longitude': center.longitude,
            'phone': center.phone, 'email': center.email, 'is_active': center.is_active
        }, status=status.HTTP_200_OK)


class CenterManageView(APIView):
    """Strictly restricted to the center creator."""
    permission_classes = [IsFarmer]

    def get_object(self, request, pk):
        return get_object_or_404(AidCenter, pk=pk, created_by=request.user)

    @swagger_auto_schema(
        operation_summary="Update own aid center",
        request_body=center_patch_body,
        responses={200: 'Updated', 403: 'Forbidden', 404: 'Not found'},
        security=[{"Bearer": []}], tags=['Locator']
    )
    def patch(self, request, pk):
        center = self.get_object(request, pk)
        for field in ['name', 'center_type', 'wilaya', 'address', 'latitude', 'longitude', 'phone', 'email', 'is_active']:
            if field in request.data:
                setattr(center, field, request.data[field])
        center.save()
        return Response({'message': 'Center updated successfully.'}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Deactivate own aid center",
        responses={204: 'Deactivated', 403: 'Forbidden', 404: 'Not found'},
        security=[{"Bearer": []}], tags=['Locator']
    )
    def delete(self, request, pk):
        center = self.get_object(request, pk)
        center.is_active = False
        center.save()
        return Response(status=status.HTTP_204_NO_CONTENT)