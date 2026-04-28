from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from Auth.permissions import IsFarmerOrAdmin
from .models import ITDASReference


calculate_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['crop', 'area_hectares', 'growth_stage'],
    properties={
        'crop': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['wheat', 'tomato', 'olive', 'date_palm', 'potato', 'onion', 'pepper', 'watermelon', 'citrus', 'barley'],
            example='wheat'
        ),
        'area_hectares': openapi.Schema(type=openapi.TYPE_NUMBER, example=3.5, description="Farm area in hectares"),
        'growth_stage': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['germination', 'vegetative', 'flowering', 'fruiting', 'maturation'],
            example='vegetative'
        ),
    }
)

calculate_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'crop': openapi.Schema(type=openapi.TYPE_STRING),
        'growth_stage': openapi.Schema(type=openapi.TYPE_STRING),
        'area_hectares': openapi.Schema(type=openapi.TYPE_NUMBER),
        'npk': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'nitrogen_kg': openapi.Schema(type=openapi.TYPE_NUMBER),
                'phosphorus_kg': openapi.Schema(type=openapi.TYPE_NUMBER),
                'potassium_kg': openapi.Schema(type=openapi.TYPE_NUMBER),
                'total_kg': openapi.Schema(type=openapi.TYPE_NUMBER),
            }
        ),
        'irrigation': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'daily_liters': openapi.Schema(type=openapi.TYPE_NUMBER),
                'daily_cubic_meters': openapi.Schema(type=openapi.TYPE_NUMBER),
                'weekly_liters': openapi.Schema(type=openapi.TYPE_NUMBER),
            }
        ),
        'source': openapi.Schema(type=openapi.TYPE_STRING),
    }
)


class CalculateInputsView(APIView):
    permission_classes = [IsFarmerOrAdmin]

    @swagger_auto_schema(
        operation_summary="Calculate NPK and irrigation needs",
        operation_description=(
            "Pure front-end style calculation — no AI involved. "
            "Based on ITDAS reference tables stored in the database. "
            "Input: crop type, area in hectares, current growth stage. "
            "Output: recommended NPK quantities in kg and daily irrigation volume in liters."
        ),
        request_body=calculate_body,
        responses={
            200: openapi.Response('Calculation result', calculate_response),
            400: 'Missing or invalid fields',
            404: 'No reference data found for this crop/stage combination',
            401: 'Unauthorized',
        },
        security=[{"Bearer": []}],
        tags=['Calculator']
    )
    def post(self, request):
        crop = request.data.get('crop', '').strip()
        growth_stage = request.data.get('growth_stage', '').strip()
        area = request.data.get('area_hectares')

        if not crop or not growth_stage or area is None:
            return Response(
                {'error': 'crop, growth_stage, and area_hectares are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            area = float(area)
            if area <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {'error': 'area_hectares must be a positive number.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_crops = ['wheat', 'tomato', 'olive', 'date_palm', 'potato', 'onion', 'pepper', 'watermelon', 'citrus', 'barley']
        valid_stages = ['germination', 'vegetative', 'flowering', 'fruiting', 'maturation']

        if crop not in valid_crops:
            return Response(
                {'error': f'Invalid crop. Must be one of: {", ".join(valid_crops)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if growth_stage not in valid_stages:
            return Response(
                {'error': f'Invalid growth_stage. Must be one of: {", ".join(valid_stages)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ref = ITDASReference.objects.get(crop=crop, growth_stage=growth_stage)
        except ITDASReference.DoesNotExist:
            return Response(
                {'error': f'No ITDAS reference data found for {crop} at {growth_stage} stage.'},
                status=status.HTTP_404_NOT_FOUND
            )

        nitrogen_kg = round(ref.npk_n * area, 2)
        phosphorus_kg = round(ref.npk_p * area, 2)
        potassium_kg = round(ref.npk_k * area, 2)
        total_npk_kg = round(nitrogen_kg + phosphorus_kg + potassium_kg, 2)

        daily_liters = round(ref.irrigation_liters_per_ha_per_day * area, 2)
        daily_cubic_meters = round(daily_liters / 1000, 3)
        weekly_liters = round(daily_liters * 7, 2)

        return Response({
            'crop': crop,
            'growth_stage': growth_stage,
            'area_hectares': area,
            'npk': {
                'nitrogen_kg': nitrogen_kg,
                'phosphorus_kg': phosphorus_kg,
                'potassium_kg': potassium_kg,
                'total_kg': total_npk_kg,
            },
            'irrigation': {
                'daily_liters': daily_liters,
                'daily_cubic_meters': daily_cubic_meters,
                'weekly_liters': weekly_liters,
            },
            'source': 'ITDAS Reference Tables — Algeria',
        }, status=status.HTTP_200_OK)


class CropStagesView(APIView):
    permission_classes = [IsFarmerOrAdmin]

    @swagger_auto_schema(
        operation_summary="List available crops and growth stages",
        operation_description="Returns all crops and growth stages available in the ITDAS reference table. Use this to populate dropdowns in the frontend.",
        responses={
            200: openapi.Response('Available crops and stages', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'crops': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                    'growth_stages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                }
            )),
            401: 'Unauthorized',
        },
        security=[{"Bearer": []}],
        tags=['Calculator']
    )
    def get(self, request):
        crops = [c[0] for c in ITDASReference.CROPS]
        stages = [s[0] for s in ITDASReference.GROWTH_STAGES]
        return Response({
            'crops': crops,
            'growth_stages': stages,
        }, status=status.HTTP_200_OK)


class ITDASReferenceTableView(APIView):
    permission_classes = [IsFarmerOrAdmin]

    @swagger_auto_schema(
        operation_summary="Get full ITDAS reference table",
        operation_description="Returns the full ITDAS NPK and irrigation reference data. Optionally filter by crop.",
        manual_parameters=[
            openapi.Parameter('crop', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, description="Filter by crop name"),
        ],
        responses={
            200: 'Full reference table',
            401: 'Unauthorized',
        },
        security=[{"Bearer": []}],
        tags=['Calculator']
    )
    def get(self, request):
        crop_filter = request.query_params.get('crop', None)
        qs = ITDASReference.objects.all().order_by('crop', 'growth_stage')

        if crop_filter:
            qs = qs.filter(crop=crop_filter)

        data = [
            {
                'crop': r.crop,
                'growth_stage': r.growth_stage,
                'npk_n_per_ha': r.npk_n,
                'npk_p_per_ha': r.npk_p,
                'npk_k_per_ha': r.npk_k,
                'irrigation_liters_per_ha_per_day': r.irrigation_liters_per_ha_per_day,
            }
            for r in qs
        ]

        return Response(data, status=status.HTTP_200_OK)