print('views')

from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic.edit import FormView
import pandas as pd

from .forms import PerioodForm

from . import Aquarea
bda = Aquarea.AquareaData()
bdi = Aquarea.IlmateenistusData()
bde = Aquarea.ElektrileviData()
bdy = Aquarea.EEYldHindData()
bdn = Aquarea.NordPoolData()


class AquareaApp():
    def __init__(self):
        print('init')
        print(
            bda.tunniandmed().index.max(),
            bde.tunniandmed().index.max(),
            bdi.tunniandmed().index.max(),
            bdn.tunniandmed().index.max(),
        )
        # Hiliseim aeg täielike andmetega:
        date_max_ceiling = min(
            bda.tunniandmed().index.max(),
            bde.tunniandmed().index.max(),
            bdi.tunniandmed().index.max(),
            bdn.tunniandmed().index.max(),
        )
        self.stopp = datetime(*date_max_ceiling[:3])
        self.start = datetime(self.stopp.year, self.stopp.month, 1) # Viimase Aquarea logikande aja kuu algus

    def cache(self, periood):
        """
        Salvestame koondatud andmed cache
        :param periood:
        :return df:
        """
        try:
            return self.cache_df[periood]
        except:
            vahemik = {'start': periood[0], 'stopp': periood[1]}
            a = bda.tunniandmed(**vahemik)
            e = bde.tunniandmed(**vahemik)
            i = bdi.tunniandmed(**vahemik)
            n = bdn.tunniandmed(**vahemik)
            y = bdy  # .kuudeandmed(**vahemik)
            df = Aquarea.BigData(a, i, e, n, y)
            print('Salvestame cache...')
            self.cache_df = {periood: df}
            return df

aquarea_app = AquareaApp()


class PerioodFormView(FormView):
    form_class = PerioodForm
    # initial = {
    #     'start_date': aquarea_app.start.strftime('%d.%m.%Y'),
    #     'stopp_date': aquarea_app.stopp.strftime('%d.%m.%Y')
    # }
    template_name = 'ajalugu/index.html'
    success_url = './'

    # def get(self, request, *args, **kwargs):
    #     form = self.form_class(initial=self.initial)
    #     return render(request, self.template_name, {'form': form})

    def get_initial(self):
        print('initial')
        initial = super(PerioodFormView, self).get_initial()
        initial.update({'start_date': aquarea_app.start.strftime('%d.%m.%Y')})
        initial.update({'stopp_date': aquarea_app.stopp.strftime('%d.%m.%Y')})
        return initial

    def form_valid(self, form):
        print('valid')
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        args = form.cleaned_data['start_date'].timetuple()[:6]
        aquarea_app.start = datetime(*args)
        args = form.cleaned_data['stopp_date'].timetuple()[:6]
        aquarea_app.stopp = datetime(*args)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['start'] = aquarea_app.start
        return context

# pole vajalik
def container_ajalugu_index_tunnikaupa(request):
    df = aquarea_app.cache((aquarea_app.start, aquarea_app.stopp))
    andmed = {
        'tunnikaupa': df.tunnikaupa().to_html(table_id='suurtabel'),
    }
    return JsonResponse(andmed)

# pole vajalik
def container_ajalugu_index_p2evakaupa(request):
    df = aquarea_app.cache((aquarea_app.start, aquarea_app.stopp))
    andmed = {
        'p2evakaupa': df.p2evakaupa().to_html(table_id='suurtabel'),
    }
    return JsonResponse(andmed)

def container_ajalugu_index_p2evakaupa_chart(request):
    """
    Moodustab koondandmetest graafiku päevade kaupa
    :param request:
    :return chart:
    """
    def nulliga_jagamine(x):
        if x[7] != 0:
            value = x[6]/x[7]
        else:
            value = 0
        return value

    df = aquarea_app.cache((aquarea_app.start, aquarea_app.stopp))
    df_chart = df.p2evakaupa()

    if df_chart.empty:
        chart = {'tyhi': True}
        return JsonResponse(chart)

    cols = df_chart.columns
    print(cols)
    categories = list(df_chart.index.to_series())
    df_chart[cols[1]][df_chart[cols[1]].isna()] = 'null' # puuduvad väärtused -> null (HighChartsi jaoks)
    bdi_outdoor_temps = list(df_chart[cols[0]])
    bda_outdoor_temps = list(df_chart[cols[1]])
    bda_con_heat_kwhs = list(df_chart[cols[3]])
    bda_con_tank_kwhs = list(df_chart[cols[4]])
    df_chart[cols[6]][df_chart[cols[6]].isna()] = 0 # puuduvad väärtused -> 0
    df_chart[cols[7]][df_chart[cols[7]].isna()] = 0 # puuduvad väärtused -> 0
    bda_gen_total_kwhs = list(df_chart[cols[6]])
    bda_con_total_kwhs = list(df_chart[cols[7]])
    bda_gen_delta_kwhs = list(df_chart[cols[6]] - df_chart[cols[7]])
    bde_con_total_EURs = list(df_chart[cols[8]])
    bda_con_total_EURs = list(df_chart[cols[9]])
    bda_COP_total = list(df_chart.apply(nulliga_jagamine, axis=1))


    # Graafiku andmeseeriate kirjeldamine
    series_bda_outdoor_temps = {
        'name': f'Keskmine temperatuur (Aquarea)',
        'data': bda_outdoor_temps,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' °C'
        },
        'yAxis': 2,
        'color': '#FF3333',
        'negativeColor': '#48AFE8',
        'visible': False
    }
    series_bdi_outdoor_temps = {
        'name': f'Keskmine temperatuur (Ilmateenistus)',
        'data': bdi_outdoor_temps,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' °C'
        },
        'yAxis': 2,
        'color': '#FF3333',
        'negativeColor': '#48AFE8',
        'visible': False
    }
    series_bde_con_total_EURs = {
        'name': f'Kulu [€] (EE+EL)',
        'data': bde_con_total_EURs,
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 2,
            'valueSuffix': ' €'
        },
        'type': 'spline',
        'dashStyle': 'Dot',
        'yAxis': 0,
        'color': 'grey',
        'visible': False
    }
    series_bda_con_total_EURs = {
        'name': f'Kulu [€] (Aquarea)',
        'data': bda_con_total_EURs,
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 2,
            'valueSuffix': ' €'
        },
        'type': 'spline',
        'yAxis': 0,
        'color': 'grey',
        'visible': False
    }
    series_bda_con_tank_kwhs = {
        'name': f'Kulu [kWh] (Aquarea)',
        'data': bda_con_tank_kwhs,
        'zIndex': 1,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' kWh'
        },
        'type': 'column',
        'stack': 0,
        'yAxis': 1,
        'color': 'orange',
    }
    series_bda_con_heat_kwhs = {
        'name': f'Kulu [kWh] (Aquarea)',
        'data': bda_con_heat_kwhs,
        'zIndex': 1,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' kWh'
        },
        'type': 'column',
        'stack': 0,
        'yAxis': 1,
        'color': 'yellow',
    }
    series_bda_gen_delta_kwhs = {
        'name': f'Kasu [kWh] (Aquarea)',
        'data': bda_gen_delta_kwhs,
        'zIndex': 1,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' kWh'
        },
        'type': 'column',
        'stack': 0,
        'yAxis': 1,
        'color': 'lightgreen',
    }
    series_bda_COP_total = {
        'name': f'Keskmine COP (Aquarea)',
        'data': bda_COP_total,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
        },
        'yAxis': 2,
        'color': 'purple',
    }
    # Graafiku joonistamine
    periood = f'{aquarea_app.start.strftime("%d.%m.%Y")}-{aquarea_app.stopp.strftime("%d.%m.%Y")}'
    bdi_outdoor_temp = f'{round(df_chart[cols[0]].mean(), 1)} °C'
    kulu_kWh = f'{int(round(sum(bda_con_total_kwhs), 0))} kWh'
    kulu_EUR = f'{sum(bda_con_total_EURs):8.2f} €'
    tulu_kWh = f'{int(round(sum(bda_gen_total_kwhs), 0))} kWh'
    try:
        COP = f'{round(sum(bda_gen_total_kwhs)/sum(bda_con_total_kwhs), 1)}'
    except:
        COP = '-'
    title = f'N={(aquarea_app.stopp-aquarea_app.start).days+1} päeva, T={bdi_outdoor_temp}: kulu {kulu_kWh}/{kulu_EUR}, tulu {tulu_kWh}/COP {COP}'
    chart = {
        'title': {
            'text': title
        },
        'xAxis': {
            'categories': categories,
            'labels': {
                'format': '{value:%d.%m.%Y}'
            }
        },
        'yAxis': [
            {
                'title': {
                    'text': ''
                },
                'labels': {
                    'format': '{value} €'
                },
                'min': 0,
                'top': 0,
                'offset': 0,
            }, {
                'title': {
                    'text': ''
                },
                'labels': {
                    'format': '{value} kWh'
                },
                'opposite': True,
                'min': 0,
                'top': 0,
                'offset': 0,
            }, {
                'title': {
                    'text': ''
                },
                'labels': {
                    'format': ''
                },
                'min': 0,
                'top': 0,
                'offset': 0,
            }
        ],
        'plotOptions': {
            'series': {
                'marker': {
                    'enabled': False
                }
            },
            'column': {
                'stacking': 'normal'
            }
        },
        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'xDateFormat': '%d.%m.%Y',
        },

        'legend': {
        },
        'series': [
            series_bda_outdoor_temps,
            series_bdi_outdoor_temps,
            # series_bda_gen_total_kwhs,
            series_bda_gen_delta_kwhs,
            series_bda_con_heat_kwhs,
            series_bda_con_tank_kwhs,
            series_bde_con_total_EURs,
            series_bda_con_total_EURs,
            series_bda_COP_total
        ]
    }
    return JsonResponse(chart)


def container_ajalugu_index_kuukaupa_chart(request):
    """
    Moodustab koondandmetest graafiku kuude kaupa
    :param request:
    :return chart:
    """
    df = aquarea_app.cache((aquarea_app.start, aquarea_app.stopp))
    df_chart = df.kuukaupa()

    if df_chart.empty:
        chart = {'tyhi': True}
        return JsonResponse(chart)

    cols = df_chart.columns
    categories = list(df_chart.index.to_series())
    bda_outdoor_temps = list(df_chart[cols[1]])
    bdi_outdoor_temps = list(df_chart[cols[0]])
    bda_con_heat_kwhs = list(df_chart[cols[2]])
    bda_con_tank_kwhs = list(df_chart[cols[3]])
    bda_gen_total_kwhs = list(df_chart[cols[5]])
    bda_con_total_kwhs = list(df_chart[cols[6]])
    bda_gen_delta_kwhs = list(df_chart[cols[5]] - df_chart[cols[6]])
    bde_con_total_EURs = list(df_chart[cols[7]])
    bda_con_total_EURs = list(df_chart[cols[8]])
    bda_COP_total = list(df_chart[cols[9]])

    # Graafiku andmeseeriate kirjeldamine
    series_bda_outdoor_temps = {
        'name': f'Keskmine temperatuur (Aquarea)',
        'data': bda_outdoor_temps,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' °C'
        },
        'yAxis': 2,
        'color': '#FF3333',
        'negativeColor': '#48AFE8',
        'visible': False
    }
    series_bdi_outdoor_temps = {
        'name': f'Keskmine temperatuur (Ilmateenistus)',
        'data': bdi_outdoor_temps,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' °C'
        },
        'yAxis': 2,
        'color': '#FF3333',
        'negativeColor': '#48AFE8',
        'visible': False
    }
    series_bde_con_total_EURs = {
        'name': f'Kulu [€] (EE+EL)',
        'data': bde_con_total_EURs,
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 2,
            'valueSuffix': ' €'
        },
        'type': 'spline',
        'dashStyle': 'Dot',
        'yAxis': 0,
        'color': 'grey',
    }
    series_bda_con_total_EURs = {
        'name': f'Kulu [€] (Aquarea)',
        'data': bda_con_total_EURs,
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 2,
            'valueSuffix': ' €'
        },
        'type': 'spline',
        'yAxis': 0,
        'color': 'grey',
    }
    series_bda_con_tank_kwhs = {
        'name': f'Kulu [kWh] (Aquarea)',
        'data': bda_con_tank_kwhs,
        'zIndex': 1,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' kWh'
        },
        'type': 'column',
        'stack': 0,
        'yAxis': 1,
        'color': 'orange',
    }
    series_bda_con_heat_kwhs = {
        'name': f'Kulu [kWh] (Aquarea)',
        'data': bda_con_heat_kwhs,
        'zIndex': 1,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' kWh'
        },
        'type': 'column',
        'stack': 0,
        'yAxis': 1,
        'color': 'yellow',
    }
    series_bda_gen_delta_kwhs = {
        'name': f'Kasu [kWh] (Aquarea)',
        'data': bda_gen_delta_kwhs,
        'zIndex': 1,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' kWh'
        },
        'type': 'column',
        'stack': 0,
        'yAxis': 1,
        'color': 'lightgreen',
    }
    series_bda_COP_total = {
        'name': f'Keskmine COP (Aquarea)',
        'data': bda_COP_total,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
        },
        'yAxis': 2,
        'color': 'purple',
    }
    # Graafiku joonistamine
    periood = f'{aquarea_app.start.strftime("%d.%m.%Y")}-{aquarea_app.stopp.strftime("%d.%m.%Y")}'
    bdi_outdoor_temp = f'{round(df_chart[cols[0]].mean(), 1)} °C'
    kulu_kWh = f'{int(round(sum(bda_con_total_kwhs), 0))} kWh'
    kulu_EUR = f'{sum(bda_con_total_EURs):8.2f} €'
    tulu_kWh = f'{int(round(sum(bda_gen_total_kwhs), 0))} kWh'
    try:
        COP = f'{round(sum(bda_gen_total_kwhs)/sum(bda_con_total_kwhs), 1)}'
    except ZeroDivisionError:
        COP = '-'
    title = f'{periood} N={(aquarea_app.stopp-aquarea_app.start).days+1} päeva, T={bdi_outdoor_temp}: kulu {kulu_kWh}/{kulu_EUR}, tulu {tulu_kWh}/COP {COP}'
    chart = {
        'title': {
            'text': ''
        },
        'xAxis': {
            'categories': categories
        },
        'yAxis': [
            {
                'title': {
                    'text': ''
                },
                'labels': {
                    'format': '{value} €'
                },
                'top': 0,
                'offset': 0,
            }, {
                'title': {
                    'text': ''
                },
                'labels': {
                    'format': '{value} kWh'
                },
                'opposite': True,
                'top': 0,
                'offset': 0,
            }, {
                'title': {
                    'text': ''
                },
                'labels': {
                    'format': ''
                },
                'top': 0,
                'offset': 0,
            }
        ],
        'plotOptions': {
            'series': {
                'marker': {
                    'enabled': False
                }
            },
            'column': {
                'stacking': 'normal'
            }
        },
        'tooltip': {
            'crosshairs': True,
            'shared': True,
        },

        'legend': {
        },
        'series': [
            series_bda_outdoor_temps,
            series_bdi_outdoor_temps,
            # series_bda_gen_total_kwhs,
            series_bda_gen_delta_kwhs,
            series_bda_con_heat_kwhs,
            series_bda_con_tank_kwhs,
            series_bde_con_total_EURs,
            series_bda_con_total_EURs,
            series_bda_COP_total
        ]
    }
    return JsonResponse(chart)


def container_ajalugu_index_cop_chart(request):
    """
    Moodustab koondandmetest COP graafiku täistemperatuuride kaupa
    :param request:
    :return chart:
    """
    df = aquarea_app.cache((aquarea_app.start, aquarea_app.stopp))
    df_chart = df.tunnikaupa().dropna() # valime tunniandmed, kus kõik andmed olemas
    df_chart = df_chart[df_chart[df_chart.columns[6]]>0] # andmed, kus Aquarea kulu > 0

    if df_chart.empty:
        chart = {'tyhi': True}
        return JsonResponse(chart)

    df_chart['cop'] = df_chart[df_chart.columns[5]] / df_chart[df_chart.columns[6]]
    g = df_chart.groupby(round(df_chart[df_chart.columns[1]]))
    cop_1h = pd.concat([g['cop'].mean(), g['cop'].count()], axis=1).round(1)
    cop_1h_list = cop_1h.reset_index().to_numpy().tolist() # koostame ridade kaupa listi graafiku jaoks

    # Pealkiri
    title = f'N={len(df_chart)} kWh>0 mõõdetud tunnivahemikku'

    # Graafiku andmeseeriate kirjeldamine
    series_bda_cop_chart = {
        'name': 'COP',
        'data': cop_1h_list,
        'marker': {
            'fillColor': {
                'radialGradient': { 'cx': 0.4, 'cy': 0.3, 'r': 0.7 },
                'stops': [
                    [0, 'rgba(255,255,255,0.5)'],
                    [1, 'lightblue']
                ]
            }
        },
        'tooltip': {
            'pointFormat': '{point.x} °C, COP={point.y}), N={point.z}'
        }
    }

    # Graafiku joonistamine
    chart = {
        'chart': {
            'type': 'bubble',
            'plotBorderWidth': 1,
            'zoomType': 'xy'
        },

        'title': {
            'text': title
        },

        'xAxis': {
            'min': -30,
            'max': 30,
            'gridLineWidth': 1,
            'startOnTick': False,
            'endOnTick': False,
        },

        'yAxis': {
            'title': {
                'text': 'COP'
            },
            'min': 0,
            'startOnTick': False,
            'endOnTick': False
        },

        'series': [series_bda_cop_chart]

    }

    return JsonResponse(chart, safe=False)