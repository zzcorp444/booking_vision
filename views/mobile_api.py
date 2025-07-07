"""
Mobile app endpoints for easier sync
"""
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def mobile_sync_endpoint(request):
    """Endpoint for mobile app to push bookings"""
    if request.method == 'POST':
        data = json.loads(request.body)
        # Process mobile app data
        return JsonResponse({'success': True})