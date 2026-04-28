from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
from Auth.permissions import IsAdminRole
from .models import WeeklyReport
from .utils import get_week_boundaries, generate_pdf_report, build_report_context, WEASYPRINT_AVAILABLE


class GenerateReportView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="Generate weekly PDF report",
        operation_description=(
            "Manually triggers the generation of a one-page weekly report summarizing diagnostics from the past week. "
            "Covers crops affected, recommended treatments, and emerging trends by region. "
            "Intended for cooperative managers. Returns the PDF file directly."
        ),
        responses={
            200: 'PDF or HTML report file returned directly',
            401: 'Unauthorized',
            403: 'Admin only',
            500: 'Report generation failed',
        },
        security=[{"Bearer": []}],
        tags=['Reports']
    )
    def post(self, request):
        week_start, week_end = get_week_boundaries()

        report = WeeklyReport.objects.create(
            generated_by=request.user,
            week_start=week_start,
            week_end=week_end,
            status='generating',
        )

        try:
            result, file_type = generate_pdf_report(week_start, week_end)

            if file_type == 'pdf':
                report.pdf_file.name = f"reports/report_{week_start}_{week_end}.pdf"
                report.status = 'ready'
                report.save()

                response = FileResponse(
                    open(result, 'rb'),
                    content_type='application/pdf'
                )
                response['Content-Disposition'] = f'attachment; filename="nabta_report_{week_start}_{week_end}.pdf"'
                return response

            else:
                report.status = 'ready'
                report.save()
                response = HttpResponse(result, content_type='text/html; charset=utf-8')
                response['Content-Disposition'] = f'inline; filename="nabta_report_{week_start}_{week_end}.html"'
                return response

        except Exception as e:
            report.status = 'failed'
            report.save()
            return Response(
                {'error': 'Report generation failed.', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportListView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="List all generated reports",
        operation_description="Returns all previously generated weekly reports. Admin only.",
        responses={
            200: openapi.Response('Reports list', openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'week_start': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                        'week_end': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'generated_by': openapi.Schema(type=openapi.TYPE_STRING),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                        'pdf_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            )),
            401: 'Unauthorized',
            403: 'Admin only',
        },
        security=[{"Bearer": []}],
        tags=['Reports']
    )
    def get(self, request):
        reports = WeeklyReport.objects.all().order_by('-created_at')
        data = [
            {
                'id': r.id,
                'week_start': r.week_start,
                'week_end': r.week_end,
                'status': r.status,
                'generated_by': str(r.generated_by),
                'created_at': r.created_at,
                'pdf_url': request.build_absolute_uri(r.pdf_file.url) if r.pdf_file else None,
            }
            for r in reports
        ]
        return Response(data, status=status.HTTP_200_OK)


class ReportPreviewView(APIView):
    permission_classes = [IsAdminRole]

    @swagger_auto_schema(
        operation_summary="Preview report data without generating PDF",
        operation_description="Returns the raw data that would be included in the weekly report. Useful to check before generating the PDF.",
        responses={
            200: 'Report data preview',
            401: 'Unauthorized',
            403: 'Admin only',
        },
        security=[{"Bearer": []}],
        tags=['Reports']
    )
    def get(self, request):
        week_start, week_end = get_week_boundaries()
        context = build_report_context(week_start, week_end)

        return Response({
            'week_start': context['week_start'],
            'week_end': context['week_end'],
            'total_diagnoses': context['total_diagnoses'],
            'top_diseases': context['top_diseases'],
            'top_crops': context['top_crops'],
            'treatments': context['treatments'],
            'wilaya_breakdown': context['wilaya_breakdown'],
            'generated_at': context['generated_at'],
            'pdf_engine': 'weasyprint' if WEASYPRINT_AVAILABLE else 'html_fallback',
        }, status=status.HTTP_200_OK)