from datetime import datetime, timedelta
import math

from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic.edit import FormView

import numpy as np
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
"""
Aquarea.Bigdata:
0 Zone1: Actual (water outlet/room/pool) temperature [°C]
1 Zone2: Actual (water outlet/room/pool) temperature [°C]
2 Actual tank temperature [°C]
3 Actual outdoor temperature [°C]
4 Heat mode energy consumption [kW]
5 Tank mode energy consumption [kW]
6 Heat mode energy generation [kW]
7 Tank mode energy generation [kW]
8 Ametlik mõõdetud temperatuur [°C]
9 Elektrienergia kulu [kWh]
10 NordPool hind [s/kWh]
11 EE üldhind [s/kWh]
12 EL üldhind [s/kWh]
13 Aquarea kulu [kWh]
14 Aquarea tulu [kWh]
15 Aquarea kulu [€]
16 Elektri kulu EE+EL [€]
17 EE leping [€]
18 EE muutuv [€]
19 Soodusaeg
"""

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

# pole vajalik
def container_ajalugu_index_kuukaupa(request):
    df = aquarea_app.cache((aquarea_app.start, aquarea_app.stopp))
    andmed = {
        'kuukaupa': df.kuukaupa().to_html(table_id='suurtabel'),
    }
    return JsonResponse(andmed)

def container_ajalugu_index_p2evakaupa_chart(request):
    """
    Moodustab koondandmetest graafiku päevade kaupa
    :param request:
    :return chart:
    """
    def nulliga_jagamine(x):
        if x[7] == 0 or x[8] == 0:
            value = 0
        else:
            value = x[7]/x[8]
        return value

    df = aquarea_app.cache((aquarea_app.start, aquarea_app.stopp))
    df_chart = df.p2evakaupa()

    if df_chart.empty:
        chart = {'tyhi': True}
        return JsonResponse(chart)

    cols = df_chart.columns

    categories = list(df_chart.index.to_series())
    df_chart.replace([np.inf, -np.inf], np.nan, inplace=True)
    bdi_outdoor_temps = list(df_chart['Ametlik mõõdetud temperatuur [°C]'].replace({np.nan: None}))
    bda_outdoor_temps = list(df_chart['Actual outdoor temperature [°C]'].replace({np.nan: None}))
    bda_zone1_temps = list(df_chart['Zone1: Actual (water outlet/room/pool) temperature [°C]'].replace({np.nan: None}))
    bda_zone2_temps = list(df_chart['Zone2: Actual (water outlet/room/pool) temperature [°C]'].replace({np.nan: None}))
    bda_con_heat_kwhs = list(df_chart['Heat mode energy consumption [kW]'].replace({np.nan: None}))
    bda_con_tank_kwhs = list(df_chart['Tank mode energy consumption [kW]'].replace({np.nan: None}))
    bda_gen_total_kwhs = list(df_chart['Aquarea tulu [kWh]'].replace({np.nan: None}))
    bda_con_total_kwhs = list(df_chart['Aquarea kulu [kWh]'].replace({np.nan: None}))
    bda_gen_delta_kwhs = list(df_chart['Aquarea tulu [kWh]'] - df_chart['Aquarea kulu [kWh]'])
    bde_con_total_EURs = list(df_chart['Elektri kulu EE+EL [€]'].replace({np.nan: None}))
    bda_con_total_EURs = list(df_chart['Aquarea kulu [€]'].replace({np.nan: None}))
    # bda_COP_total = list(df_chart.apply(nulliga_jagamine, axis=1))
    bda_COP_total = list(df_chart['COP'].replace({np.nan: None}))
    bda_COP_heat = list(df_chart['COP_heat'].replace({np.nan: None}))
    bda_COP_tank = list(df_chart['COP_tank'].replace({np.nan: None}))

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
    series_bda_zone1_temps = {
        'name': f'Keskmine küttevee temperatuur (Z1)',
        'data': bda_zone1_temps,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' °C'
        },
        'yAxis': 2,
        'color': '#DDDDDD',
        # 'negativeColor': '#48AFE8',
        'visible': False
    }
    series_bda_zone2_temps = {
        'name': f'Keskmine küttevee temperatuur (Z2)',
        'data': bda_zone2_temps,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
            'valueSuffix': ' °C'
        },
        'yAxis': 2,
        'color': '#DDDDDD',
        # 'negativeColor': '#48AFE8',
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
    series_bda_COP_heat = {
        'name': f'Keskmine COP (heat) (Aquarea)',
        'data': bda_COP_heat,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
        },
        'yAxis': 2,
        'color': 'purple',
        'visible': False
    }
    series_bda_COP_tank = {
        'name': f'Keskmine COP (tank) (Aquarea)',
        'data': bda_COP_tank,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
        },
        'yAxis': 2,
        'color': 'purple',
        'visible': False
    }
    # Graafiku joonistamine
    periood = f'{aquarea_app.start.strftime("%d.%m.%Y")}-{aquarea_app.stopp.strftime("%d.%m.%Y")}'
    bdi_outdoor_temp = f'{round(df_chart[cols[0]].mean(), 1)} °C'
    kulu_kWh = f'{int(round(sum(bda_con_total_kwhs), 1))} kWh'
    kulu_EUR = f'{sum(bda_con_total_EURs):8.2f} €'
    tulu_kWh = f'{int(round(sum(bda_gen_total_kwhs), 1))} kWh'
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
            'type': 'category',
            # 'labels': {
            #     'format': '{text}'
            # }
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
            series_bda_zone1_temps,
            series_bda_zone2_temps,
            # series_bda_gen_total_kwhs,
            series_bda_gen_delta_kwhs,
            series_bda_con_heat_kwhs,
            series_bda_con_tank_kwhs,
            series_bde_con_total_EURs,
            series_bda_con_total_EURs,
            series_bda_COP_total,
            series_bda_COP_heat,
            series_bda_COP_tank,
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
    df_chart.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_chart.replace({np.nan: None}, inplace=True)

    if df_chart.empty:
        chart = {'tyhi': True}
        return JsonResponse(chart)

    # df_chart.to_csv('kontroll.csv')

    cols = df_chart.columns
    categories = list(df_chart.index.to_series())
    bda_outdoor_temps = list(df_chart['Actual outdoor temperature [°C]'])
    bdi_outdoor_temps = list(df_chart['Ametlik mõõdetud temperatuur [°C]'])
    bda_con_heat_kwhs = list(df_chart['Heat mode energy consumption [kW]'])
    bda_con_tank_kwhs = list(df_chart['Tank mode energy consumption [kW]'])
    bda_gen_total_kwhs = list(df_chart['Aquarea tulu [kWh]'])
    bda_con_total_kwhs = list(df_chart['Aquarea kulu [kWh]'])
    bda_gen_delta_kwhs = list(df_chart['Aquarea tulu [kWh]'] - df_chart['Aquarea kulu [kWh]'])
    bde_con_total_EURs = list(df_chart['Elektri kulu EE+EL [€]'])
    bda_con_total_EURs = list(df_chart['Aquarea kulu [€]'])
    bda_COP_total = list(df_chart['COP'])
    bda_COP_heat = list(df_chart['COP_heat'])
    bda_COP_tank = list(df_chart['COP_tank'])

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
        'visible': False
    }
    series_bda_COP_heat = {
        'name': f'Keskmine COP (heat) (Aquarea)',
        'data': bda_COP_heat,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
        },
        'yAxis': 2,
        'color': 'purple',
    }
    series_bda_COP_tank = {
        'name': f'Keskmine COP (tank) (Aquarea)',
        'data': bda_COP_tank,
        'type': 'spline',
        'zIndex': 2,
        'tooltip': {
            'valueDecimals': 1,
        },
        'yAxis': 2,
        'color': 'purple',
        'visible': False
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
            series_bda_COP_total,
            series_bda_COP_heat,
            series_bda_COP_tank,
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
    df_chart = df.tunnikaupa()

    df_chart.replace([np.inf, -np.inf], np.nan, inplace=True)

    # perioodi temperatuuriandmed
    bdi_temp_histogram_data = list(df_chart['Actual outdoor temperature [°C]'].dropna())
    # ainult kütteperioodi andmed (15.05-15.09)
    mask = (
            ((df_chart.index.get_level_values(1) > 9) | (df_chart.index.get_level_values(1) < 5)) |
            (
                    ((df_chart.index.get_level_values(1) == 5) & (df_chart.index.get_level_values(2) < 16)) |
                    ((df_chart.index.get_level_values(1) == 9) & (df_chart.index.get_level_values(2) > 14))
            )
    )
    bdi_temp_histogram_data_heating_period = list(df_chart.loc[mask]['Actual outdoor temperature [°C]'].dropna())

    df_chart.dropna(inplace=True) # valime tunniandmed, kus kõik andmed olemas
    df_chart = df_chart[df_chart['Aquarea kulu [kWh]']>0] # andmed, kus Aquarea kulu > 0

    if df_chart.empty:
        chart = {'tyhi': True}
        return JsonResponse(chart)

    # COP andmed
    df_chart['cop'] = (
            (df_chart['Heat mode energy generation [kW]'] + df_chart['Tank mode energy generation [kW]']) /
            (df_chart['Heat mode energy consumption [kW]'] + df_chart['Tank mode energy consumption [kW]'])
    )
    df_chart['cop_heat'] = df_chart['Heat mode energy generation [kW]'] / df_chart['Heat mode energy consumption [kW]']
    df_chart['cop_tank'] = df_chart['Tank mode energy generation [kW]'] / df_chart['Tank mode energy consumption [kW]']

    g = df_chart.groupby(round(df_chart['Actual outdoor temperature [°C]']))
    cop_1h = pd.concat([g['cop'].mean(), g['cop'].count()], axis=1).round(1)
    cop_1h.replace([np.inf, -np.inf], np.nan, inplace=True)
    # cop_1h = cop_1h.replace({np.nan: None, np.inf: None})
    cop_1h.dropna(inplace=True)
    # cop_1h.to_csv('kontroll_cop_1h.csv')
    cop_1h_list = cop_1h.reset_index().to_numpy().tolist() # koostame ridade kaupa listi graafiku jaoks

    cop_1h_heat = pd.concat([g['cop_heat'].mean(), g['cop_heat'].count()], axis=1).round(1)
    # cop_1h_heat = cop_1h_heat.replace({np.nan: None, np.inf: None})
    cop_1h_heat.replace([np.inf, -np.inf], np.nan, inplace=True)
    cop_1h_heat.dropna(inplace=True)
    # cop_1h_heat.to_csv('kontroll_cop_1h_heat.csv')
    cop_1h_heat_list = cop_1h_heat.reset_index().to_numpy().tolist()  # koostame ridade kaupa listi graafiku jaoks

    cop_1h_tank = pd.concat([g['cop_tank'].mean(), g['cop_tank'].count()], axis=1).round(1)
    # cop_1h_tank = cop_1h_tank.replace({np.nan: None})
    cop_1h_tank.replace([np.inf, -np.inf], np.nan, inplace=True)
    cop_1h_tank = cop_1h_tank.dropna()
    # cop_1h_tank.to_csv('kontroll_cop_1h_tank.csv')
    cop_1h_tank_list = cop_1h_tank.reset_index().to_numpy().tolist()  # koostame ridade kaupa listi graafiku jaoks

    # Kütmise elektrikulu andmed kWh
    con_1h = pd.concat([g['Heat mode energy consumption [kW]'].mean(), g['Heat mode energy consumption [kW]'].count()], axis=1).round(1)
    con_1h.replace([np.inf, -np.inf], np.nan, inplace=True)
    con_1h.dropna(inplace=True)
    con_1h.to_csv('kontroll_con_1h.csv')
    con_1h_list = con_1h.reset_index().to_numpy().tolist()  # koostame ridade kaupa listi graafiku jaoks

    # Pealkiri
    title = f'N={len(df_chart)} kWh>0 mõõdetud tunnivahemikku'

    # Graafiku andmeseeriate kirjeldamine
    series_bda_cop_series = {
        'name': 'COP',
        'type': 'bubble',
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
        },
        'visible': False
    }
    series_bda_cop_heat_series = {
        'name': 'COP (heat)',
        'type': 'bubble',
        'data': cop_1h_heat_list,
        'marker': {
            'fillColor': {
                'radialGradient': {'cx': 0.4, 'cy': 0.3, 'r': 0.7},
                'stops': [
                    [0, 'rgba(255,255,255,0.5)'],
                    [1, 'yellow']
                ]
            }
        },
        'tooltip': {
            'pointFormat': '{point.x} °C, COP={point.y}), N={point.z}'
        },
        'visible': True
    }

    series_bda_cop_tank_series = {
        'name': 'COP (tank)',
        'type': 'bubble',
        'data': cop_1h_tank_list,
        'marker': {
            'fillColor': {
                'radialGradient': {'cx': 0.4, 'cy': 0.3, 'r': 0.7},
                'stops': [
                    [0, 'rgba(255,255,255,0.5)'],
                    [1, 'orange']
                ]
            }
        },
        'tooltip': {
            'pointFormat': '{point.x} °C, COP={point.y}), N={point.z}'
        },
        'visible': False
    }

    series_bda_con_series = {
        'name': 'Kütmise energiakulu kWh',
        'type': 'bubble',
        'data': con_1h_list,
        'marker': {
            'fillColor': {
                'radialGradient': {'cx': 0.4, 'cy': 0.3, 'r': 0.7},
                'stops': [
                    [0, 'rgba(255,255,255,0.5)'],
                    [1, 'lightblue']
                ]
            }
        },
        'tooltip': {
            'pointFormat': '{point.x} °C, kWh={point.y}), N={point.z}'
        },
        'visible': True
    }

    series_bdi_temp_histogram_series = {
        'name': 'Histogram',
        'type': 'histogram',
        'xAxis': 0,
        'yAxis': 1,
        'baseSeries': 2,
        'binsNumber': 'sturges',
        'zIndex': -1,
        'visible': False
    }

    series_bdi_temp_histogram_heating_period_series = {
        'name': 'Histogram (15.09-15.05)',
        'type': 'histogram',
        'xAxis': 0,
        'yAxis': 1,
        'baseSeries': 3,
        'binsNumber': 'sturges',
        'zIndex': -1,
        'visible': False
    }

    # Graafiku joonistamine
    chart = {
        'chart': {
            # 'type': 'bubble',
            'plotBorderWidth': 1,
            'zoomType': 'xy'
        },

        'title': {
            'text': title
        },

        'xAxis': [
            {
                'min': -30,
                'max': 30,
                'gridLineWidth': 1,
                'startOnTick': False,
                'endOnTick': False,
            }
        ],

        'yAxis': [
            {
                'title': {
                    'text': 'COP'
                },
                'min': 0,
                'startOnTick': False,
                'endOnTick': False,
                # 'minorTicks': True,
                'plotLines': [{
                    'color': '#FF0000',
                    'width': 2,
                    'value': 1,
                    # 'label': {
                    #     'text': 'COP=1'
                    # }
                }]
            }, {
                'title': {
                    'text': 'Histogram'
                },
                'opposite': True,
                'gridLineWidth': 0
            }
        ],

        'plotOptions': {
            'histogram': {
                'dataLabels': {
                    'enabled': True,
                    'pointFormat': ''
                },
                'tooltip': {
                    'headerFormat': '<b>{series.name}</b><br>',
                    'pointFormat': '{index}. {point.x:.1f} to {point.x2:.1f}, {point.y}.',
                    'clusterFormat': 'Clustered points: {point.clusterPointsAmount}'
                },
            }
        },

        'series': [
            series_bdi_temp_histogram_series,
            series_bdi_temp_histogram_heating_period_series,
            bdi_temp_histogram_data,
            bdi_temp_histogram_data_heating_period,
            series_bda_cop_series,
            series_bda_cop_heat_series,
            series_bda_cop_tank_series,
            series_bda_con_series,
        ]

    }

    return JsonResponse(chart, safe=False)

from ajalugu.Aquarea import ElektrileviData, NordPoolData
class PerioodElektrienergiaFormView(FormView):
    form_class = PerioodForm
    template_name = 'ajalugu/elektrienergia.html'
    success_url = './elektrienergia'

    def get_initial(self):
        print('initial')
        initial = super(PerioodElektrienergiaFormView, self).get_initial()
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

def container_elektrilevi_n2dalakaupa_chart(request):
    """
    Tagastab Elektrienergia andmed graafiku heatmap n2dalap2ev/tund jaoks
    :param request:
    :return andmed:list
    """
    bde = ElektrileviData()
    query = bde.n2dalaandmed(start=aquarea_app.start, stopp=aquarea_app.stopp)
    data = query['andmed']
    return JsonResponse(
        {
            'andmed': [(key[1], key[0], round(item, 1)) for key, item in data[data.keys()[0]].items()],
            'count': query['count'],
        },
        safe=False)

def container_nordpool_n2dalakaupa_chart(request):
    """
    Tagastab Nordpooli andmed graafiku heatmap n2dalap2ev/tund jaoks
    :param request:
    :return andmed:list
    """
    bdn = NordPoolData()
    query = bdn.n2dalaandmed(start=aquarea_app.start, stopp=aquarea_app.stopp)
    data = query['andmed']
    return JsonResponse(
        {
            'andmed': [(key[1], key[0], round(item, 1)) for key, item in data[data.keys()[0]].items()],
            'count': query['count'],
        },
        safe=False)

def container_cop_hourly_chart(request):
    """
    Tagastab Aquarea COP andmed graafiku jaoks
    :param request:
    :return andmed:list
    """
    andmed = dict()
    df = bda.tunniandmed()

    for temp in [-5, 0, 5]:
        filter = (
            (df['Heat mode energy consumption [kW]'] > 0) &
            (df['Heat mode energy generation [kW]'] > 0) &
            (df['Actual outdoor temperature [°C]'] == temp)
        )
        df_filtered = df[filter].copy()
        values = df_filtered['Heat mode energy generation [kW]'] / df_filtered['Heat mode energy consumption [kW]']
        df_filtered['cop'] = values
        df_filtered['date'] = df_filtered.apply(lambda row: datetime(*row.name), axis = 1)
        andmed[str(temp)] = [[date.timestamp()*1000, cop] for date, cop in zip(df_filtered['date'].tolist(), df_filtered['cop'].tolist())]
    return JsonResponse(
        {
            'andmed': andmed,
            'count': df.shape[0],
        },
        safe=False
    )

