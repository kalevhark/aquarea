print('ajalugu.urls')

from django.urls import path
from django.conf import settings

from . import views

app_name = 'ajalugu'

urlpatterns = [
    # path('', views.index, name='index'),
    path(
        '',
        views.PerioodFormView.as_view(),
        name='index'
    ),
    path(
        'container_ajalugu_index_p2evakaupa/',
        views.container_ajalugu_index_p2evakaupa,
        name='container_ajalugu_index_p2evakaupa'
    ),
    path(
        'container_ajalugu_index_p2evakaupa_chart/',
        views.container_ajalugu_index_p2evakaupa_chart,
        name='container_ajalugu_index_p2evakaupa_chart'
    ),
    path(
        'container_ajalugu_index_kuukaupa/',
        views.container_ajalugu_index_kuukaupa,
        name='container_ajalugu_index_kuukaupa'
    ),
    path(
        'container_ajalugu_index_kuukaupa_chart/',
        views.container_ajalugu_index_kuukaupa_chart,
        name='container_ajalugu_index_kuukaupa_chart'
    ),
    path(
        'container_ajalugu_index_cop_chart/',
        views.container_ajalugu_index_cop_chart,
        name='container_ajalugu_index_cop_chart'
    ),
    path(
        'elektrienergia',
        views.PerioodElektrienergiaFormView.as_view(),
        name='elektrienergia'
    ),
    path(
        'container_elektrilevi_n2dalakaupa_chart/',
        views.container_elektrilevi_n2dalakaupa_chart,
        name='container_elektrilevi_n2dalakaupa_chart'
    ),
    path(
        'container_nordpool_n2dalakaupa_chart/',
        views.container_nordpool_n2dalakaupa_chart,
        name='container_nordpool_n2dalakaupa_chart'
    ),
]

