import time
from calendar import monthrange
from datetime import datetime, timedelta, timezone
import json

import xml.etree.ElementTree as ET

from django.conf import settings
from django.http import JsonResponse

from django.shortcuts import render
import pytz

import requests
# import tinytuya # https://pypi.org/project/tinytuya/

import app.utils.aquarea_service_util as aqserv
# import app.utils.aquarea_smart_util as aqsmrt
from app.utils.astral_util import get_day_or_night_plotbands
import app.utils.ephem_util as ephem_data
# from app.utils import ledvance_util
import app.utils.nps_util as nps_util

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

m2rgiga = lambda i: ("+" if i > 0 else "") + str(i)

# Tagastab kuupäeva 1 kuu tagasi
def kuu_tagasi(dt):
    year = dt.year
    if dt.month > 1:
        month = dt.month - 1
    else:
        month = 12
        year = year - 1
    if dt.day > monthrange(year, month)[1]:
        day = monthrange(year, month)[1]
    else:
        day = dt.day
    return datetime(year, month, day)

# Abifunktsioon numbriliste näitajate iseloomustamiseks värvikoodiga
def colorclass(temp, colorset):
    colorclass = colorset['default']
    if temp:
        for level in colorset['levels']:
            if temp > level[0]:
                colorclass = level[1]
                break
    return colorclass

def get_aquarea_serv_data(request=None):
    data = aqserv.arvuta_aquareaservice_andmed(verbose=False)
    return JsonResponse(data) if request else data

# Tagastab -12h kuni +12h vahemiku x-telje väärtused
def get_xaxis_categories(request=None):
    date_today = datetime.now()
    date_today_range_24h = [date_today + timedelta(hours=n) for n in range(-11, 13)]
    categories = [f'{hour.hour}' for hour in date_today_range_24h]
    return JsonResponse(categories, safe=False) if request else categories

# Ilmateenistuse mõõtmisandmed
def get_ilmateenistus_now(request=None):
    # Loeme Ilmateenistuse viimase mõõtmise andmed veebist
    jaam = 'Valga'
    href = 'http://www.ilmateenistus.ee/ilma_andmed/xml/observations.php'
    r = requests.get(href)
    try:
        root = ET.fromstring(r.text.strip())
    except:
        # Kontrollime kas vaatlusandmed ikkagi olemas
        observation_exists = r.text.find('<observations')
        if observation_exists > 0:
            root = ET.fromstring(r.text[observation_exists:])
        else:
            return None
    ilmaandmed = dict()
    # Mõõtmise aeg
    dt = datetime.fromtimestamp(int(root.attrib['timestamp']))
    ilmaandmed['timestamp'] = pytz.timezone('Europe/Tallinn').localize(dt)
    station = root.findall("./station/[name='"+jaam+"']")
    for el in station:
        for it in el:
            data = it.text
            # Kui ei ole tekstiväli, siis teisendame float tüübiks
            if it.tag not in ['name',
                              'station',
                              'phenomenon',
                              'phenomenon_observer']:
                try:
                    data = float(data)
                except:
                    data = None
            ilmaandmed[it.tag] = data

    airtemperature_colorset = {'default': 'blue', 'levels': [(0, 'red')]}
    ilmaandmed['airtemperature_colorclass'] = colorclass(
        ilmaandmed['airtemperature'],
        airtemperature_colorset
    )
    relativehumidity_colorset = {'default': 'red', 'levels': [(60, 'blue'), (40, 'green')]}
    ilmaandmed['relativehumidity_colorclass'] = colorclass(
        ilmaandmed['relativehumidity'],
        relativehumidity_colorset
    )
    return JsonResponse(ilmaandmed) if request else ilmaandmed

def get_yrno_forecast(request=None, hours=12):
    altitude = "64"
    lat = "57.77781"
    lon = "26.0473"
    # yr.no API
    url = 'https://api.met.no/weatherapi/locationforecast/2.0/complete'
    params = {
        'lat': lat,
        'lon': lon,
        'altitude': altitude
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
    }
    r = requests.get(
        url,
        headers=headers,
        params=params
    )
    if r.status_code == 200:
        YRno_forecast = {
            'meta': {
                'Expires': r.headers['Expires'],
                'Last-Modified': r.headers['Last-Modified']
            },
            'data': json.loads(r.text)
        }
    else:
        YRno_forecast = {}

    if YRno_forecast:
        data = YRno_forecast['data']
        # yrno API annab uue ennustuse iga tunni aja tagant
        # alates sellele järgnevast täistunnist
        timeseries = data['properties']['timeseries']
        now = datetime.now(timezone.utc).isoformat()
        # Filtreerime hetkeajast hilisemad järgmise 48h ennustused
        filter_pastnow = filter(lambda hour: hour['time'] > now, timeseries)

        timeseries_hours = list(filter_pastnow)[:hours]

        next_12hour_outdoor_temp = [
            hour['data']['instant']['details']['air_temperature']
            # hour
            for hour
            in timeseries_hours
        ]
        next_12hour_outdoor_prec_min = [
            hour['data']['next_1_hours']['details']['precipitation_amount_min']
            for hour
            in timeseries_hours
        ]
        next_12hour_outdoor_prec_err = [
            hour['data']['next_1_hours']['details']['precipitation_amount_max'] -
            hour['data']['next_1_hours']['details']['precipitation_amount_min']
            for hour
            in timeseries_hours
        ]
        data = {
            'next_12hour_outdoor_temp': next_12hour_outdoor_temp,
            'next_12hour_outdoor_prec_min': next_12hour_outdoor_prec_min,
            'next_12hour_outdoor_prec_err': next_12hour_outdoor_prec_err
        }
        YRno_forecast.update(data)

    return JsonResponse(YRno_forecast) if request else YRno_forecast

# Andmed põrandakütte juhtseadmelt
def get_ezr_data(request=None):
    # Loeme Ilmateenistuse viimase mõõtmise andmed veebist
    href = f'http://{settings.EZR_IP_ADDRESS}/data/static.xml'
    r = requests.get(href)
    try:
        root = ET.fromstring(r.text)
    except:
        return None

    ezr_data = dict()

    # Viimase värskenduse kuupäev
    ezr_data_datatime = root[0].find('DATETIME').text
    ezr_data['datetime'] = pytz.timezone('Europe/Tallinn')\
        .localize(datetime.fromisoformat(ezr_data_datatime))

    # Kütteahelate staatus (HEATCTRL_STATE '0'-kinni, '1'-lahti)
    for heatctrl in root.iter('HEATCTRL'):
        inuse = heatctrl.find('INUSE').text
        if inuse == '1':
            nr = heatctrl.get('nr')
            actor = heatctrl.find('ACTOR').text
            actor_percent = heatctrl.find('ACTOR_PERCENT').text
            heatctrl_state = heatctrl.find('HEATCTRL_STATE').text
            ezr_data[f'nr{nr}'] = {
                'actor': actor,
                'actor_percent': actor_percent,
                'heatctrl_state': heatctrl_state
            }

    # Ruumide näitajad
    for heatarea in root.iter('HEATAREA'):
        nr = heatarea.get('nr')
        heatarea_name = heatarea.find('HEATAREA_NAME').text
        t_actual = heatarea.find('T_ACTUAL').text
        t_target = heatarea.find('T_TARGET').text
        # print(nr, heatarea_name, t_actual, t_target)
        ezr_data[f'nr{nr}'].update(
            {'heatarea_name': heatarea_name,
             't_actual': t_actual,
             't_target': t_target}
        )

    return JsonResponse(ezr_data) if request else ezr_data

# dashboardi avaleht
def index(request):
    date_today = datetime.now()
    date_today = pytz.timezone('Europe/Tallinn').localize(date_today)
    categories = get_xaxis_categories()

    sun_str = ephem_data.get_sun_str(date_today)
    moon_str = ephem_data.get_moon_str(date_today)
    title = f'<strong>{date_today.strftime("%d.%m.%Y %H:%M")} {sun_str} {moon_str}</strong>'
    chart_24h = {
        'chart': {
            'type': 'column'
        },
        'title': {
            'useHTML': True,
            'text': title
        },
        'xAxis': {
            'categories': categories,
            'plotBands': get_day_or_night_plotbands(date_today),
            'plotLines': [{
                'value': 11 + date_today.minute/60,
                'label': {
                    'text': date_today.strftime("%H:%M"),
                    'style': {
                        'color': 'gray',
                        "fontSize": "10px"
                    }
                },
                'color': 'gray',
                'dashStyle': 'Dot',
                'width': 2,
                'zIndex': 3
            }]
        },
        'yAxis': [{ # Primary yAxis
            'title': {
                'text': 'Kulu kW/h / Sademed mm',
            },
            'labels': {
                'format': '{value}',
                'style': {
                    'color': 'Highcharts.getOptions().colors[0]'
                }
            },
        }, { # Secondary yAxis
            'title': {
                'text': 'Välistemperatuur (Sulevi 9a)',
            },
            'tickInterval': 1,
            'minorTickInterval': 0.5,
            'labels': {
                'format': '{value}°C',
                'plotLines': [{  # zero plane
                    'value': 0,
                    'color': '#BBBBBB',
                    'width': 1,
                    'zIndex': 2
                }],
            },
            'opposite': True
        }],
        'tooltip': {
            'headerFormat': '<b>kell {point.x}:00</b><br/>',
            'pointFormat': '{series.name}: {point.y}<br/>Kokku: {point.stackTotal}'
        },
        # 'annotations': [{
        #     'labels': [{
        #         'point': {
        #             'x': 11 + date_today.minute/60,
        #             'xAxis': 0,
        #             'y': aquarea_temp_val,
        #             'yAxis': 0
        #         },
        #         'text': f'{aquarea_temp_val}°C'
        #     }],
        #     'labelOptions': {
        #         'backgroundColor': 'rgba(255,255,255,0.5)',
        #         'borderColor': 'silver',
        #         'style': {'fontSize': '1em'},
        #     }
        # }],
        'plotOptions': {
            'column': {
                'stacking': 'normal',
                'dataLabels': {
                    'enabled': False
                },
                'grouping': False
            }
        },
        'series': [
            {
                'id': 'last_12hour_outdoor_temp',
                'name': 'Välistemperatuur',
                'type': 'spline',
                'data': [], # last_12hour_outdoor_temp, # [-7.0, -6.9, 9.5, 14.5, 18.2, 21.5, -25.2, -26.5, 23.3, 18.3, 13.9, 9.6],
                'yAxis': 1,
                'tooltip': {
                    'pointFormat': '{series.name}: {point.y}',
                    'valueSuffix': '°C'
                },
                'zIndex': 3,
                'color': '#FF3333',
                'negativeColor': '#48AFE8'
            }, {
                'id': 'next_12hour_outdoor_temp',
                'name': 'Välistemperatuur (prognoos)',
                'type': 'spline',
                'data': [],
                'yAxis': 1,
                'tooltip': {
                    'pointFormat': '{series.name}: {point.y}',
                    'valueSuffix': '°C'
                },
                'zIndex': 3,
                'dashStyle': 'shortdot',
                'color': '#FF3333',
                'negativeColor': '#48AFE8'
            }, {
                'id': 'last_12hour_tot_gen_plus',
                'name': 'Kasu',
                'yAxis': 0,
                'pointWidth': 3,
                'data': [],
                'color': '#00ff00',
                'zIndex': 2,
                'stack': 'aquarea'
            }, {
                'id': 'last_12hour_tot_gen_minus',
                'name': 'Kahju',
                'yAxis': 0,
                'pointWidth': 3,
                'data': [],
                'color': '#d0312d',
                'zIndex': 3,
                # 'stack': 'aquareaminus'
            }, {
                'id': 'last_12hour_consum_heat',
                'name': 'Küte',
                'yAxis': 0,
                'pointWidth': 3,
                'data': [], # last_12hour_consum_heat,
                'color': '#F5C725',
                'zIndex': 2,
                'stack': 'aquarea'
            }, {
                'id': 'last_12hour_consum_tank',
                'name': 'Vesi',
                'yAxis': 0,
                'pointWidth': 3,
                'data': [], # last_12hour_consum_tank,
                'color': '#0E98BA',
                'zIndex': 2,
                'stack': 'aquarea'
            }, {
                'id': 'next_12hour_outdoor_prec_err',
                'type': 'column',
                'name': 'Sademed (prognoos err)',
                'data': [],
                'color': {
                    'pattern': {
                        'path': {
                            'd': 'M 0 0 L 5 5 M 4.5 -0.5 L 5.5 0.5 M -0.5 4.5 L 0.5 5.5',
                        },
                        'width': 5,
                        'height': 5,
                        'color': '#68CFE8',
                    }
                },
                'yAxis': 0,
                'pointWidth': 20,
                'grouping': False,
                'tooltip': {
                    # 'pointFormat': '{series.name}: {point.y}',
                    'valueSuffix': ' mm'
                },
                'zIndex': 2,
                'stack': 'prec'
            }, {
                'id': 'next_12hour_outdoor_prec_min',
                'type': 'column',
                'name': 'Sademed (prognoos min)',
                'data': [],
                'color': '#68CFE8',
                'yAxis': 0,
                'pointWidth': 20,
                'grouping': False,
                'tooltip': {
                    # 'pointFormat': '{series.name}: {point.y}',
                    'valueSuffix': ' mm'
                },
                'zIndex': 2,
                'stack': 'prec'
            }, {
                'id': 'nps_12plus12_hour_prices',
                'name': 'EE börsihind',
                'type': 'spline',
                'data': [], # täidetakse ajax teenusega get_nps_12plus12_hours_data
                'yAxis': 1,
                'tooltip': {
                    # 'headerFormat': '<b>kell {point.x}:00</b><br/>',
                    'pointFormat': '{series.name}: {point.y}<br/>Viimase 30p keskmine: {point.last_30days_prices_mean} s/kWh',
                    'valueSuffix': ' s/kWh'
                },
                'zIndex': 5,
                'dashStyle': 'shortdot',
                'color': '#9E32A8',
                # 'negativeColor': '#48AFE8'
            },
        ]
    }
    context = {
        # 'date_today': date_today,
        # 'date_today_last7days': date_today_last7days,
        # 'aquarea_data': aquarea_data,
        'chart_24h': chart_24h,
    }
    return render(request, 'app/index.html', context)

#
# Tagastab:
# - tänase ja eilse päeva andmed
# - 12h graafiku
# - jooksva seadme staatuse
# - nädalagraafiku
#
def get_aquarea_smrt_data_day(request):
    t2na = datetime.now()
    eile = t2na - timedelta(days=1)
    jooksev_p2ev = t2na.day

    # Logime sisse
    session, login_resp = aqsmrt.login()

    # Hetkenäitajad
    status = aqsmrt.get_status(session)
    # print(status)

    # Tänane kulu
    t2na_string = t2na.strftime('%Y-%m-%d')
    t2na_consum = aqsmrt.consum(session, t2na_string)
    # print(t2na_consum)
    t2na_heat = sum(filter(None, t2na_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
    t2na_tank = sum(filter(None, t2na_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Eilne kulu
    eile_string = eile.strftime('%Y-%m-%d')
    eile_consum = aqsmrt.consum(session, eile_string)
    eile_heat = sum(filter(None, eile_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
    eile_tank = sum(filter(None, eile_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Nädalagraafik
    weekly_timer = aqsmrt.get_weekly_timer(session)

    # Logime välja
    _ = aqsmrt.logout(session)

    # Loob 24h graafiku
    # Aquearea näitab hetketunni tarbimist - näiteks kell 00:30 näidatakse viimase poole tunni tarbimist
    # 12 viimast tundi = hetketund ja 11 eelmist
    date_today_range_24h = [t2na + timedelta(hours=n) for n in range(-11, 13)]
    # categories = [f'{hour.hour}' for hour in date_today_range_24h]
    # Küsime andmed
    date_today_hour = t2na.hour
    # last12_range_start, last12_range_end = 24 + date_today_hour - 11, 24 + date_today_hour + 1
    last12_range_start, last12_range_end = 24 + date_today_hour - 12, 24 + date_today_hour + 0
    # Täna
    date_today_consum_heat = t2na_consum['dateData'][0]['dataSets'][0]['data'][0]['values']
    date_today_consum_tank = t2na_consum['dateData'][0]['dataSets'][0]['data'][2]['values']
    date_today_outdoor_temp = t2na_consum['dateData'][0]['dataSets'][3]['data'][1]['values']
    # Eile
    date_yesterday_consum_heat = eile_consum['dateData'][0]['dataSets'][0]['data'][0]['values']
    date_yesterday_consum_tank = eile_consum['dateData'][0]['dataSets'][0]['data'][2]['values']
    date_yesterday_outdoor_temp = eile_consum['dateData'][0]['dataSets'][3]['data'][1]['values']
    # Eelnevad 12h
    last_12hour_consum_heat = (date_yesterday_consum_heat + date_today_consum_heat)[last12_range_start:last12_range_end]
    last_12hour_consum_tank = (date_yesterday_consum_tank + date_today_consum_tank)[last12_range_start:last12_range_end]
    last_12hour_outdoor_temp = (date_yesterday_outdoor_temp + date_today_outdoor_temp)[
                               last12_range_start:last12_range_end]

    aquarea_data = {
        'status': status,
        't2na_heat': t2na_heat,
        't2na_tank': t2na_tank,
        'eile_heat': eile_heat,
        'eile_tank': eile_tank,
        'weekly_timer': weekly_timer,
        'last_12hour_consum_heat': last_12hour_consum_heat,
        'last_12hour_consum_tank': last_12hour_consum_tank,
        'last_12hour_outdoor_temp': last_12hour_outdoor_temp
    }
    return JsonResponse(aquarea_data)

#
# Tagastab:
# - jooksva kuu, eelmise kuu ja eelmise aasta sama kuu andmed
#
def get_aquarea_smrt_data_month(request):
    t2na = datetime.now()
    jooksev_aasta = t2na.year
    jooksev_kuu = t2na.month
    # jooksev_p2ev = t2na.day
    kuu_eelmine = kuu_tagasi(t2na)

    kuu_heat = ''
    kuu_tank = ''
    kuu_eelmine_heat = ''
    kuu_eelmine_tank = ''
    kuu_aasta_tagasi_heat = ''
    kuu_aasta_tagasi_tank = ''

    # Logime sisse
    session, login_resp = aqsmrt.login()

    # Jooksva kuu kulu
    kuu_string = t2na.strftime('%Y-%m')
    kuu_consum = aqsmrt.consum(session, kuu_string)
    if kuu_consum:
        kuu_heat = sum(filter(None, kuu_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
        kuu_tank = sum(filter(None, kuu_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Eelmise kuu kulu
    kuu_eelmine_string = kuu_eelmine.strftime('%Y-%m')
    kuu_eelmine_consum = aqsmrt.consum(session, kuu_eelmine_string)
    if kuu_eelmine_consum:
        kuu_eelmine_heat = sum(filter(None, kuu_eelmine_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
        kuu_eelmine_tank = sum(filter(None, kuu_eelmine_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Eelmise aasta sama kuu kulu
    kuu_aasta_tagasi_string = datetime(jooksev_aasta - 1, jooksev_kuu, 1).strftime('%Y-%m')
    kuu_aasta_tagasi_consum = aqsmrt.consum(session, kuu_aasta_tagasi_string)
    if kuu_aasta_tagasi_consum:
        kuu_aasta_tagasi_heat = sum(
            filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
        kuu_aasta_tagasi_tank = sum(
            filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Logime välja
    _ = aqsmrt.logout(session)

    # if all([kuu_heat, kuu_heat, kuu_eelmine_heat, kuu_eelmine_tank, kuu_aasta_tagasi_heat, kuu_aasta_tagasi_tank]):
    if True:
        aquarea_data = {
            'kuu_heat': kuu_heat,
            'kuu_tank': kuu_tank,
            'kuu_eelmine_heat': kuu_eelmine_heat,
            'kuu_eelmine_tank': kuu_eelmine_tank,
            'kuu_aasta_tagasi_heat': kuu_aasta_tagasi_heat,
            'kuu_aasta_tagasi_tank': kuu_aasta_tagasi_tank,
        }
    else:
        aquarea_data = {}
    return JsonResponse(aquarea_data)

#
# Tagastab:
# - jooksva aasta, jooksva persioodi ja eelmise perioodi andmed
#
def get_aquarea_smrt_data_year(request):
    t2na = datetime.now()
    jooksev_aasta = t2na.year
    jooksev_kuu = t2na.month
    jooksev_p2ev = t2na.day

    jooksva_perioodi_heat = ''
    jooksva_perioodi_tank = ''
    eelmise_perioodi_heat = ''
    eelmise_perioodi_tank = ''

    # Logime sisse
    # time.sleep(60)
    session, login_resp = aqsmrt.login()

    # Eelmise aasta sama kuu kulu
    kuu_aasta_tagasi_string = datetime(jooksev_aasta - 1, jooksev_kuu, 1).strftime('%Y-%m')
    kuu_aasta_tagasi_consum = aqsmrt.consum(session, kuu_aasta_tagasi_string)

    # Periood = 1.07.(aasta-1)-30.06.(aasta)
    jooksva_aasta_string = t2na.strftime('%Y')
    eelmise_aasta_string = datetime(t2na.year - 1, 1, 1).strftime('%Y')

    if t2na >= datetime(t2na.year, 7, 1):  # Kui kütteperioodi esimene poolaasta (alates 1. juulist)
        jooksva_aasta_consum = aqsmrt.consum(session, jooksva_aasta_string)
        eelmise_aasta_consum = aqsmrt.consum(session, eelmise_aasta_string)
        if all([jooksva_aasta_consum, eelmise_aasta_consum]):
            # Arvutame jooksva perioodi kulu
            # Jooksva perioodi 1. poolaasta küttevee kulu
            jooksva_perioodi_heat = sum(
                filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:]))
            # Jooksva perioodi 1. tarbevee kulu
            jooksva_perioodi_tank = sum(
                filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:]))
            # Arvutame eelmise perioodi kulu
            # Eelmise perioodi 1. poolaasta küttevee kulu
            eelmise_perioodi_heat = sum(
                filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:jooksev_kuu - 1]))
            eelmise_perioodi_heat += sum(
                filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:jooksev_p2ev]))
            # Eelmise perioodi 1. tarbevee kulu
            eelmise_perioodi_tank = sum(
                filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:jooksev_kuu - 1]))
            eelmise_perioodi_tank += sum(
                filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:jooksev_p2ev]))
    else:  # Kui kütteperioodi teine poolaasta (kuni 30. juunini)
        jooksva_aasta_consum = aqsmrt.consum(session, jooksva_aasta_string)
        eelmise_aasta_consum = aqsmrt.consum(session, eelmise_aasta_string)
        yle_eelmise_aasta_string = datetime(t2na.year - 2, 1, 1).strftime('%Y')
        yle_eelmise_aasta_consum = aqsmrt.consum(session, yle_eelmise_aasta_string)
        if all([jooksva_aasta_consum, eelmise_aasta_consum, yle_eelmise_aasta_consum]):
            # Jooksva perioodi 1. poolaasta küttevee kulu
            jooksva_perioodi_heat = sum(
                filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:7]))
            # Jooksva perioodi 1. poolaasta tarbevee kulu
            jooksva_perioodi_tank = sum(
                filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:7]))
            # Lisame
            # Jooksva perioodi 2. poolaasta küttevee kulu
            jooksva_perioodi_heat += sum(
                filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:]))
            # Jooksva perioodi 2. poolaasta tarbevee kulu
            jooksva_perioodi_tank += sum(
                filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:]))
            # Arvutame eelmise perioodi kulu
            # Eelmise perioodi 1. poolaasta küttevee kulu
            eelmise_perioodi_heat = sum(
                filter(None, yle_eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:]))
            # Eelmise perioodi 1. poolaasta tarbevee kulu
            eelmise_perioodi_tank = sum(
                filter(None, yle_eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:]))
            # Eelmise perioodi 2. poolaasta küttevee kulu
            eelmise_perioodi_heat += sum(
                filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:jooksev_kuu - 1]))
            eelmise_perioodi_heat += sum(
                filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:jooksev_p2ev]))
            # Eelmise perioodi 2. poolaasta tarbevee kulu
            eelmise_perioodi_tank += sum(
                filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:jooksev_kuu - 1]))
            eelmise_perioodi_tank += sum(
                filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:jooksev_p2ev]))

    # Logime välja
    _ = aqsmrt.logout(session)
    # if all([jooksva_perioodi_heat, jooksva_perioodi_tank, eelmise_perioodi_heat, eelmise_perioodi_tank]):
    #     aquarea_data = {
    #         'jooksva_perioodi_heat': jooksva_perioodi_heat,
    #         'jooksva_perioodi_tank': jooksva_perioodi_tank,
    #         'eelmise_perioodi_heat': eelmise_perioodi_heat,
    #         'eelmise_perioodi_tank': eelmise_perioodi_tank,
    #     }
    # else:
    #     aquarea_data = {}
    aquarea_data = {
        'jooksva_perioodi_heat': jooksva_perioodi_heat,
        'jooksva_perioodi_tank': jooksva_perioodi_tank,
        'eelmise_perioodi_heat': eelmise_perioodi_heat,
        'eelmise_perioodi_tank': eelmise_perioodi_tank,
    }
    return JsonResponse(aquarea_data)

def get_tuyaapi_data_old(request):
    TUYA_DEVICE_ID = settings.TUYA_DEVICE_ID
    TUYA_IP_ADDRESS = settings.TUYA_IP_ADDRESS
    TUYA_LOCAL_KEY = settings.TUYA_LOCAL_KEY
    d = tinytuya.OutletDevice(TUYA_DEVICE_ID, TUYA_IP_ADDRESS, TUYA_LOCAL_KEY)
    d.set_version(3.3)
    tuyaapi_data = d.status()
    return JsonResponse(tuyaapi_data)


def get_tuyaapi_data(request):
    data = ledvance_util.status()
    return JsonResponse(data)

def turnon_ledvance(request):
    data = ledvance_util.turnon(ledvance=1, hours=1)
    return JsonResponse(data)

def get_nps_12plus12_hours_data(request):
    nps_12plus12_hour_prices_data = nps_util.get_nps_12plus12_hour_prices_ee_marginaaliga()
    return JsonResponse(nps_12plus12_hour_prices_data)