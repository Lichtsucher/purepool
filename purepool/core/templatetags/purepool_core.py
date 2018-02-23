from django.conf import settings
from django import template

register = template.Library()

@register.simple_tag
def network_list():
    return settings.BIBLEPAY_NETWORKS