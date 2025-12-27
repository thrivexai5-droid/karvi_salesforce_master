from django.urls import path
from . import views

app_name = 'quotation'

urlpatterns = [
    path('', views.quotation_view, name='index'),
    path('generate/', views.generate_quotation, name='generate'),
]