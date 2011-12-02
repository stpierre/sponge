from sponge.models import Configuration

def set(name, value):
    try:
        item = Configuration.objects.get(pk=name)
        item.value = value
    except Configuration.DoesNotExist:
        item = Configuration(name=name, value=value)

    item.save()
    return value

def get(name, default=None):
    try:
        item = Configuration.objects.get(pk=name)
        return item.value
    except Configuration.DoesNotExist:
        return default
