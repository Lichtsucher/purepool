from django.conf import settings

def add_purepool_data(request):
    """ adds the name and other basic infos about the pool to the context """
    return {
        'POOL_NAME': settings.POOL_NAME,
        'POOL_WEBSITE_URL': settings.POOL_WEBSITE_URL,
        'POOL_INTERFACE_URL': settings.POOL_INTERFACE_URL,
    }
