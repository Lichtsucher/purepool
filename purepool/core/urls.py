from django.conf import settings
from django.urls import path

urlpatterns = []

if settings.ENABLE_POOL_INTERFACE:
    from purepool.interface.views import action
    
    urlpatterns += [
        path('Action.aspx', action, name="action_aspx")
    ]
    
if settings.ENABLE_POOL_FRONTEND:
    from purepool.frontend.views import index, index_redirect, howtojoin, miner, statistics
    
    urlpatterns += [
        path('', index_redirect, name="index"),
        path('<str:network>/', index, name="index_network"),
        path('<str:network>/howtojoin/', howtojoin, name="howtojoin"),        
        path('<str:network>/statistics', statistics, name="statistics"),
        path('<str:network>/miner/<str:address>/', miner, name="miner")
    ]