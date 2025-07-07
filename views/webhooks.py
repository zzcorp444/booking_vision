from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json

@csrf_exempt
def webhook_receiver(request, channel_name):
    """Receive webhooks from channels"""
    if request.method == 'POST':
        data = json.loads(request.body)
        # Process webhook data
        # Verify webhook signature if provided
        return HttpResponse(status=200)