from pulp.common.dateutils import parse_iso8601_datetime
from django import template
import django.template.defaultfilters as defaultfilters

register = template.Library()

def iso8601date(value, arg=None):
    return defaultfilters.date(parse_iso8601_datetime(value), arg)

register.filter('iso8601date', iso8601date)
