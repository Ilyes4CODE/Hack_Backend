from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from Auth.permissions import IsFarmerOrAdmin, IsAdminRole
from .models import GalleryPhoto


class GalleryListView(APIView):
    permission_classes = [IsFarmerOrAdmin]

    @swagger_auto_schema(
        operation_summary="Browse community disease gallery",
        operation_description=(
            "Returns approved photos submitted by farmers. "
            "Filterable by crop type and wilaya. "
            "Acts as a visual map of active disease outbreaks across Algeria."
        ),
        manual_parameters=[
            openapi.Parameter('crop', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                enum=['wheat','tomato','olive','date_palm','potato','onion','pepper','watermelon','citrus','barley']),
            openapi.Parameter('wilaya', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('disease_tag', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={
            200: openapi.Response('Gallery photos', openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'image_url': openapi.Schema(type=openapi.TYPE_STRING),
                        'crop': openapi.Schema(type=openapi.TYPE_STRING),
                        'wilaya': openapi.Schema(type=openapi.TYPE_STRING),
                        'disease_tag': openapi.Schema(type=openapi.TYPE_STRING),
                        'submitted_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                    }
                )
            )),
            401: 'Unauthorized',
        },
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def get(self, request):
        qs = GalleryPhoto.objects.filter(is_approved=True).order_by('-submitted_at')

        crop = request.query_params.get('crop')
        wilaya = request.query_params.get('wilaya')
        disease_tag = request.query_params.get('disease_tag')

        if crop:
            qs = qs.filter(crop=crop)
        if wilaya:
            qs = qs.filter(wilaya__icontains=wilaya)
        if disease_tag:
            qs = qs.filter(disease_tag__icontains=disease_tag)

        data = [
            {
                'id': p.id,
                'image_url': request.build_absolute_uri(p.image.url),
                'crop': p.crop,
                'wilaya': p.wilaya,
                'disease_tag': p.disease_tag,
                'submitted_at': p.submitted_at,
            }
            for p in qs
        ]
        return Response(data, status=status.HTTP_200_OK)


class GallerySubmitView(APIView):
    permission_classes = [IsFarmerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]
    @swagger_auto_schema(
        operation_summary="Submit a photo to the community gallery",
        operation_description=(
            "Farmer submits a photo of a diseased crop. "
            "Photo is anonymized — no user identity is stored or returned. "
            "Submitted photos require admin approval before appearing in the gallery."
        ),
        manual_parameters=[
            openapi.Parameter('image', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('crop', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('wilaya', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('disease_tag', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
        ],
        consumes=['multipart/form-data'],
        responses={
            201: openapi.Response('Photo submitted', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )),
            400: 'Missing required fields',
            401: 'Unauthorized',
        },
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def post(self, request):
        image = request.FILES.get('image')
        crop = request.data.get('crop', '').strip()
        wilaya = request.data.get('wilaya', '').strip()
        disease_tag = request.data.get('disease_tag', '').strip()

        if not image:
            return Response({'error': 'Image is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not crop:
            return Response({'error': 'Crop is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not wilaya:
            return Response({'error': 'Wilaya is required.'}, status=status.HTTP_400_BAD_REQUEST)

        valid_crops = ['wheat','tomato','olive','date_palm','potato','onion','pepper','watermelon','citrus','barley']
        if crop not in valid_crops:
            return Response(
                {'error': f'Invalid crop. Must be one of: {", ".join(valid_crops)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        photo = GalleryPhoto.objects.create(
            image=image,
            crop=crop,
            wilaya=wilaya,
            disease_tag=disease_tag,
            is_approved=False,
        )

        return Response({
            'message': 'Photo submitted successfully. It will appear after admin approval.',
            'id': photo.id,
        }, status=status.HTTP_201_CREATED)


class GalleryAdminListView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="List all pending photos (admin)",
        operation_description="Returns all unapproved photos waiting for admin review.",
        responses={
            200: 'Pending photos list',
            401: 'Unauthorized',
            403: 'Admin only',
        },
        security=[{"Bearer": []}],
        tags=['Gallery — Admin']
    )
    def get(self, request):
        qs = GalleryPhoto.objects.filter(is_approved=False).order_by('-submitted_at')
        data = [
            {
                'id': p.id,
                'image_url': request.build_absolute_uri(p.image.url),
                'crop': p.crop,
                'wilaya': p.wilaya,
                'disease_tag': p.disease_tag,
                'submitted_at': p.submitted_at,
            }
            for p in qs
        ]
        return Response(data, status=status.HTTP_200_OK)


class GalleryApproveView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="Approve a submitted photo (admin)",
        operation_description="Marks a submitted photo as approved so it appears in the public gallery.",
        responses={
            200: 'Photo approved',
            401: 'Unauthorized',
            403: 'Admin only',
            404: 'Photo not found',
        },
        security=[{"Bearer": []}],
        tags=['Gallery — Admin']
    )
    def patch(self, request, pk):
        photo = get_object_or_404(GalleryPhoto, pk=pk)
        photo.is_approved = True
        photo.save()
        return Response({'message': 'Photo approved and now visible in the gallery.'}, status=status.HTTP_200_OK)


class GalleryDeleteView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="Delete a gallery photo (admin)",
        operation_description="Permanently deletes a photo from the gallery. Admin only.",
        responses={
            204: 'Deleted',
            401: 'Unauthorized',
            403: 'Admin only',
            404: 'Photo not found',
        },
        security=[{"Bearer": []}],
        tags=['Gallery — Admin']
    )
    def delete(self, request, pk):
        photo = get_object_or_404(GalleryPhoto, pk=pk)
        photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)