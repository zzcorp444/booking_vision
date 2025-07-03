"""
Custom template filters for Booking Vision
"""
from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Look up a value in a dictionary using a key"""
    if dictionary and key:
        return dictionary.get(key, [])
    return []

@register.filter
def date(value, format_string):
    """Format a date"""
    if hasattr(value, 'strftime'):
        return value.strftime(format_string)
    return value