from datetime import timedelta
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
import os
import requests

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


def get_week_boundaries():
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday() + 7)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_groq_recommendations(top_diseases, top_crops, wilaya_breakdown):
    if not top_diseases and not top_crops:
        return "No diagnostic data available this week to generate recommendations."

    diseases_text = ", ".join([f"{d} ({c} cases)" for d, c in top_diseases]) if top_diseases else "none"
    crops_text = ", ".join([f"{c} ({n} cases)" for c, n in top_crops]) if top_crops else "none"
    wilayas_text = ", ".join(wilaya_breakdown.keys()) if wilaya_breakdown else "unknown"

    prompt = f"""You are an expert agronomist working with Algerian farmers.

Based on this week's crop disease diagnostic data:
- Most affected crops: {crops_text}
- Diseases detected: {diseases_text}
- Regions reporting: {wilayas_text}

Write a short agronomic advisory (4-6 sentences) for cooperative managers covering:
1. The most urgent disease threat this week
2. One practical action farmers should take immediately
3. One emerging trend to watch next week

Be direct, practical, and specific. Write in English."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.4,
            },
            timeout=15,
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip().strip('"')
        return "AI recommendations unavailable this week."
    except Exception:
        return "AI recommendations unavailable this week."


def build_report_context(week_start, week_end):
    from diagnosis.models import DiagnosisResult

    diagnoses = DiagnosisResult.objects.filter(
        created_at__date__gte=week_start,
        created_at__date__lte=week_end,
    ).select_related('user')

    total = diagnoses.count()

    crops_affected = {}
    diseases_found = {}
    treatments = {}
    wilaya_breakdown = {}

    for d in diagnoses:
        crops_affected[d.crop_name] = crops_affected.get(d.crop_name, 0) + 1
        diseases_found[d.disease_name] = diseases_found.get(d.disease_name, 0) + 1
        if d.treatment:
            treatments[d.disease_name] = d.treatment
        wilaya = getattr(d.user, 'wilaya', 'Unknown')
        wilaya_breakdown[wilaya] = wilaya_breakdown.get(wilaya, 0) + 1

    top_diseases = sorted(diseases_found.items(), key=lambda x: x[1], reverse=True)[:5]
    top_crops = sorted(crops_affected.items(), key=lambda x: x[1], reverse=True)

    ai_recommendations = get_groq_recommendations(top_diseases, top_crops, wilaya_breakdown)

    return {
        'week_start': week_start,
        'week_end': week_end,
        'total_diagnoses': total,
        'top_diseases': top_diseases,
        'top_crops': top_crops,
        'treatments': treatments,
        'wilaya_breakdown': wilaya_breakdown,
        'ai_recommendations': ai_recommendations,
        'generated_at': timezone.now(),
    }


def generate_pdf_report(week_start, week_end):
    context = build_report_context(week_start, week_end)
    html_string = render_to_string('reports/weekly_report.html', context)

    if not WEASYPRINT_AVAILABLE:
        return html_string.encode('utf-8'), 'html'

    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"report_{week_start}_{week_end}.pdf"
    filepath = os.path.join(reports_dir, filename)

    HTML(string=html_string).write_pdf(filepath)
    return filepath, 'pdf'