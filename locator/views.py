from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from Auth.permissions import IsAdminRole, IsFarmerOrAdmin
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import AidCenter
from .utils import sort_centers_by_distance


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
        'distance_km': openapi.Schema(type=openapi.TYPE_NUMBER),
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


class NearestCentersView(APIView):
    permission_classes = [IsFarmerOrAdmin]

    @swagger_auto_schema(
        operation_summary="Get nearest aid centers",
        operation_description="Returns the closest agricultural aid centers based on user GPS coordinates. Optionally filter by center type.",
        manual_parameters=[lat_param, lon_param, limit_param, type_param],
        responses={
            200: openapi.Response('List of nearest centers', openapi.Schema(type=openapi.TYPE_ARRAY, items=center_response)),
            400: 'Invalid or missing lat/lon parameters',
            401: 'Authentication required',
            403: 'Farmer or admin role required',
        },
        tags=['Locator']
    )
    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except (TypeError, ValueError):
            return Response(
                {'error': 'Valid lat and lon are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = int(request.query_params.get('limit', 5))
        center_type = request.query_params.get('type', None)

        qs = AidCenter.objects.filter(is_active=True)
        if center_type:
            qs = qs.filter(center_type=center_type)

        ranked = sort_centers_by_distance(list(qs), lat, lon)[:limit]

        data = []
        for center, dist in ranked:
            data.append({
                'id': center.id,
                'name': center.name,
                'type': center.center_type,
                'wilaya': center.wilaya,
                'address': center.address,
                'latitude': center.latitude,
                'longitude': center.longitude,
                'phone': center.phone,
                'email': center.email,
                'distance_km': dist,
            })

        return Response(data, status=status.HTTP_200_OK)


class CenterDetailView(APIView):
    permission_classes = [IsFarmerOrAdmin]

    @swagger_auto_schema(
        operation_summary="Get a single aid center",
        operation_description="Returns full details of one active aid center by its ID.",
        responses={
            200: openapi.Response('Center detail', center_response),
            401: 'Authentication required',
            403: 'Farmer or admin role required',
            404: 'Center not found or inactive',
        },
        tags=['Locator']
    )
    def get(self, request, pk):
        center = get_object_or_404(AidCenter, pk=pk, is_active=True)
        data = {
            'id': center.id,
            'name': center.name,
            'type': center.center_type,
            'wilaya': center.wilaya,
            'address': center.address,
            'latitude': center.latitude,
            'longitude': center.longitude,
            'phone': center.phone,
            'email': center.email,
        }
        return Response(data, status=status.HTTP_200_OK)


class CenterListView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="List all aid centers (admin)",
        operation_description="Returns all active aid centers. Filterable by wilaya and type. Admin only.",
        manual_parameters=[wilaya_param, type_param],
        responses={
            200: openapi.Response('Centers list', openapi.Schema(type=openapi.TYPE_ARRAY, items=center_response)),
            401: 'Authentication required',
            403: 'Admin access required',
        },
        tags=['Locator — Admin']
    )
    def get(self, request):
        wilaya = request.query_params.get('wilaya', None)
        center_type = request.query_params.get('type', None)

        qs = AidCenter.objects.filter(is_active=True)
        if wilaya:
            qs = qs.filter(wilaya__icontains=wilaya)
        if center_type:
            qs = qs.filter(center_type=center_type)

        data = [
            {
                'id': c.id,
                'name': c.name,
                'type': c.center_type,
                'wilaya': c.wilaya,
                'latitude': c.latitude,
                'longitude': c.longitude,
                'is_active': c.is_active,
            }
            for c in qs
        ]
        return Response(data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create a new aid center (admin)",
        operation_description="Creates a new agricultural aid center. Admin only.",
        request_body=center_create_body,
        responses={
            201: openapi.Response('Center created', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'id': openapi.Schema(type=openapi.TYPE_INTEGER), 'message': openapi.Schema(type=openapi.TYPE_STRING)})),
            400: 'Missing required fields',
            401: 'Authentication required',
            403: 'Admin access required',
        },
        tags=['Locator — Admin']
    )
    def post(self, request):
        required = ['name', 'center_type', 'wilaya', 'latitude', 'longitude']
        for field in required:
            if not request.data.get(field):
                return Response(
                    {'error': f'{field} is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        center = AidCenter.objects.create(
            name=request.data['name'],
            center_type=request.data['center_type'],
            wilaya=request.data['wilaya'],
            address=request.data.get('address', ''),
            latitude=float(request.data['latitude']),
            longitude=float(request.data['longitude']),
            phone=request.data.get('phone', ''),
            email=request.data.get('email', ''),
        )

        return Response({'id': center.id, 'message': 'Center created.'}, status=status.HTTP_201_CREATED)


class CenterManageView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="Update an aid center (admin)",
        operation_description="Partially updates any field of an existing aid center. Admin only.",
        request_body=center_patch_body,
        responses={
            200: openapi.Response('Updated', openapi.Schema(type=openapi.TYPE_OBJECT, properties={'message': openapi.Schema(type=openapi.TYPE_STRING)})),
            401: 'Authentication required',
            403: 'Admin access required',
            404: 'Center not found',
        },
        tags=['Locator — Admin']
    )
    def patch(self, request, pk):
        center = get_object_or_404(AidCenter, pk=pk)
        fields = ['name', 'center_type', 'wilaya', 'address', 'latitude', 'longitude', 'phone', 'email', 'is_active']
        for field in fields:
            if field in request.data:
                setattr(center, field, request.data[field])
        center.save()
        return Response({'message': 'Center updated.'}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Deactivate an aid center (admin)",
        operation_description="Soft-deletes a center by setting is_active to False. Admin only.",
        responses={
            204: 'Center deactivated',
            401: 'Authentication required',
            403: 'Admin access required',
            404: 'Center not found',
        },
        tags=['Locator — Admin']
    )
    def delete(self, request, pk):
        center = get_object_or_404(AidCenter, pk=pk)
        center.is_active = False
        center.save()
        return Response({'message': 'Center deactivated.'}, status=status.HTTP_204_NO_CONTENT)