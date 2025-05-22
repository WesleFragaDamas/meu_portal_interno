# meu_portal_interno/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dimensionamento/', include('dimensionamento.urls', namespace='dimensionamento')),
    path('escalas/', include('escalas.urls', namespace='escalas')), # NOVA LINHA AQUI
    path('', include('core.urls', namespace='core')),
]