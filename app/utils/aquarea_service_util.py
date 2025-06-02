from datetime import datetime, timedelta
import csv
import json
import os
from pathlib import Path, PurePath
import pickle
import re
from tabnanny import verbose
import time
import requests
import urllib3
# Vaigistame ssl veateated
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# import numpy as np
import pandas as pd

try:
    from django.conf import settings
    AQUAREA_USR = settings.AQUAREA_USR
    AQUAREA_PWD_SERVICE = settings.AQUAREA_PWD_SERVICE
    AQUAREA_SELECTEDGWID = settings.AQUAREA_SELECTEDGWID
    AQUAREA_SELECTEDDEVICEID = settings.AQUAREA_SELECTEDDEVICEID
except:
    # import os
    # os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard.settings'
    # import django
    # from django.test.utils import setup_test_environment
    # django.setup()
    from app.utils import dev_conf
    AQUAREA_USR = dev_conf.AQUAREA_USR
    AQUAREA_PWD_SERVICE = dev_conf.AQUAREA_PWD_SERVICE
    AQUAREA_SELECTEDGWID = dev_conf.AQUAREA_SELECTEDGWID
    AQUAREA_SELECTEDDEVICEID = dev_conf.AQUAREA_SELECTEDDEVICEID

print('aquarea:', AQUAREA_SELECTEDGWID, AQUAREA_SELECTEDDEVICEID)

import pytz

def float_or_none(datafield:str):
    try:
        return round(float(datafield), 1)
    except:
        return None

def float_or_zero(datafield:str):
    try:
        return float(datafield)
    except:
        return 0
#
# Aquarea Service andmete lugemine failist
#
def loe_logiandmed_failist(filename, verbose=True):
    with open(filename) as f:
        # andmed_raw = f.read()
        andmed_raw_dict = json.loads(f.read())
        logiandmed_raw = andmed_raw_dict['logData']
        logiandmed_dict = json.loads(logiandmed_raw)
        date_min_timestamp = int(min(logiandmed_dict.keys())) / 1000
        date_max_timestamp = int(max(logiandmed_dict.keys())) / 1000
        date_min = datetime.fromtimestamp(date_min_timestamp)
        date_max = datetime.fromtimestamp(date_max_timestamp)
        logiandmed_dict_firstrow = [key for key in logiandmed_dict.keys()][0]
        print(f'Andmed {date_min}-{date_max} ridu {len(logiandmed_dict.keys())} veerge {len(logiandmed_dict[logiandmed_dict_firstrow])}')
        
        # Töötleme andmed graafiku jaoks
        elements71 = [ # andmesett kuni 24.03.2024
            11,  # Tank water set temperature [°C]
            33,  # Actual tank temperature [°C]
            34,  # Actual outdoor temperature [°C]
            35,  # Inlet water temperature [°C]
            36,  # Outlet water temperature [°C]
            37,  # Zone1: Water temperature [°C]
            38,  # Zone2: Water temperature [°C]
            39,  # Zone1: Water temperature (Target) [°C]
            40,  # Zone2: Water temperature (Target) [°C]
            65,  # Heat mode energy consumption [kW]
            66,  # Heat mode energy generation [kW]
            69,  # Tank mode energy consumption [kW]
            70,  # Tank mode energy generation [kW]
        ]

        elements81 = [ # andmesett alates 25.03.2024
            11,  # Tank water set temperature [°C]
            40,  # Actual tank temperature [°C]
            41,  # Actual outdoor temperature [°C]
            42,  # Inlet water temperature [°C]
            43,  # Outlet water temperature [°C]
            44,  # Zone1: Water temperature [°C]
            45,  # Zone2: Water temperature [°C]
            46,  # Zone1: Water temperature (Target) [°C]
            47,  # Zone2: Water temperature (Target) [°C]
            72,  # Heat mode energy consumption [kW]
            74,  # Heat mode energy generation [kW]
            78,  # Tank mode energy consumption [kW]
            79,  # Tank mode energy generation [kW]
        ]

        for key in logiandmed_dict.keys():
            print(datetime.fromtimestamp(int(key)/1000), end=': ')
            andmerea_pikkus = len(logiandmed_dict[key])
            if andmerea_pikkus == 81:
                print([logiandmed_dict[key][el] for el in elements81])
            else:
                print([logiandmed_dict[key][el] for el in elements71])
        
    return logiandmed_dict


def loe_logiandmed_veebist(verbose=True):
    # vana lahendus ette antud tunnid
    # dateTime_last_hours = datetime.now() - timedelta(hours=hours-1)
    # dateTime_last_hours_fullhour = datetime(
    #     dateTime_last_hours.year,
    #     dateTime_last_hours.month,
    #     dateTime_last_hours.day,
    #     dateTime_last_hours.hour
    # )

    # uus lahendus küsime alati eelmise päeva algusest alates
    dateTime_last_hours = datetime.now() - timedelta(days=1)
    dateTime_last_hours_fullhour = datetime(
        dateTime_last_hours.year,
        dateTime_last_hours.month,
        dateTime_last_hours.day,
        0 # alates keskööst
    )

    LOGIN_URL = 'https://aquarea-service.panasonic.com/installer/api/auth/login'
    REQUEST_URL = 'https://aquarea-service.panasonic.com/installer/home'
    USERINFO_URL = 'https://aquarea-service.panasonic.com/installer/functionUserInformation'
    LOGINFO_URL = 'https://aquarea-service.panasonic.com/installer/api/data/log'
    LOGOUT_URL = 'https://aquarea-service.panasonic.com/installer/api/auth/logout'

    # Panasonicu kliendiparameetrid
    gwUid = '01236fba-5dc8-445a-92ff-30f6c27082c1'
    deviceId = '008007B197792584001434545313831373030634345373130434345373138313931304300000000'

    params = {
        'var.loginId': AQUAREA_USR,
        'var.password': AQUAREA_PWD_SERVICE,
        'var.inputOmit': 'false'
    }
    headers = {
        "Host": "aquarea-service.panasonic.com",
        "Connection": "keep-alive",
        "Content-Length": "0",
        "Cache-Control": "max-age=0",
        "Origin": 'https://aquarea-service.panasonic.com',
        "Upgrade-Insecure-Requests": "1",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Sec-Fetch-Site": "same-origin",
        "Referer": 'https://aquarea-service.panasonic.com/installer/home',
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en;q=0.9,ja;q=0.7",
    }

    with requests.Session() as session:
        if verbose:
            print('Küsime võtmed...', end=' ')
        post = session.post(
            LOGIN_URL,
            params=params,
            headers=headers,
            verify=False
        )
        if verbose:
            print(post.status_code)
            print(post.text[:4000])

        AWSALB = post.cookies['AWSALB']
        AWSALBCORS = post.cookies['AWSALBCORS']
        JSESSIONID = post.cookies['JSESSIONID']
        headers["Cookie"] = f"AWSALB={AWSALB}; AWSALBCORS={AWSALBCORS}; JSESSIONID={JSESSIONID}"

        r = session.get(
            REQUEST_URL,
            headers=headers,
        )
        # print(r.status_code)
        # print(r.text[:2000])
        m = re.search("shiesuahruefutohkun = '(\S+)'", r.text)
        shiesuahruefutohkun = m.group(0).split(' = ')[1].replace("'", "")
        #if verbose:
        #    print(shiesuahruefutohkun)

        # Valime kasutaja
        payload = {
            'var.functionSelectedGwUid': gwUid
        }
        u = session.post(
            USERINFO_URL,
            data=payload,
            headers=headers,
            verify=False
        )

        if verbose:
            print('Kontrollime kasutajat (>-1)', u.text.find('Kalev'))

        # Küsime soovitud tundide logi
        logDate = int(dateTime_last_hours_fullhour.timestamp() * 1000)

        items = '%2C'.join([f'{n}' for n in range(0, 81)])  # '%2C' = ','
        logItems = '%7B%22logItems%22%3A%5B' + items + '%5D%7D'  # '{"logItems":[' + items + ']}'

        PARAMS = f"var.deviceId={deviceId}&var.target=0&var.startDate={logDate}&var.logItems={logItems}&shiesuahruefutohkun={shiesuahruefutohkun}"
        logiandmed_raw = session.post(
            '?'.join([LOGINFO_URL, PARAMS]),
            headers=headers
        )
        # print(logiandmed_raw.request.headers)
        logiandmed_json = logiandmed_raw.json()

        logiandmed_dict = json.loads(logiandmed_json['logData'])
        # print('Logiandmed:', logiandmed_dict)

        if verbose:
            print('Logiandmed:', logiandmed_dict)
            mxd = int(max(logiandmed_dict.keys())) / 1000
            mnd = int(min(logiandmed_dict.keys())) / 1000
            print(f'Andmed: {datetime.fromtimestamp(mnd)}-{datetime.fromtimestamp(mxd)}, {len(logiandmed_dict)} rida')

        resp = session.post(
            LOGOUT_URL,
            headers=headers,
            verify=False)
        if verbose:
            print(resp.text)
    return logiandmed_dict

def arvuta_aquareaservice_andmed(verbose=False):
    hours = 12
    logiandmed_dict = loe_logiandmed_veebist(verbose=verbose)
    dateTime_last_hours = datetime.now() - timedelta(hours=hours-1)
    dateTime_last_hours_fullhour = datetime(
        dateTime_last_hours.year,
        dateTime_last_hours.month,
        dateTime_last_hours.day,
        dateTime_last_hours.hour
    )
    t2na = datetime.now()
    eile = t2na - timedelta(days=1)

    # Töötleme andmed graafiku jaoks
    elements = [
        0, # Operation [1:Off, 2:On]
        2, # Mode [1:Tank, 2:Heat, 3:Cool, 8:Auto, 9:Auto(Heat), 10:Auto(Cool)]
        3, # Tank [1:Off, 2:On]
        4, # Zone1-Zone2 On-Off [1:On-Off, 2:Off-On, 3:On-On]
        41,  # Actual outdoor temperature [°C]
        42,  # Inlet water temperature [°C]
        43,  # Outlet water temperature [°C]
        44,  # Zone1: Water temperature [°C]
        45,  # Zone2: Water temperature [°C]
        72,  # Heat mode energy consumption [kW]
        74,  # Heat mode energy generation [kW]
        78,  # Tank mode energy consumption [kW]
        79,  # Tank mode energy generation [kW]
        11,  # Tank water set temperature [°C]
        40,  # Actual tank temperature [°C]
        46,  # Zone1: Water temperature (Target) [°C]
        47,  # Zone2: Water temperature (Target) [°C]
    ]

    operation_actual = dict()
    # graafiku andmeread
    act_outd_temp = []
    ilet_water_temp = []
    olet_water_temp = []
    z1_water_temp = []
    z2_water_temp = []
    z1_water_temp_target = []
    z2_water_temp_target = []
    tank_temp = []
    tank_temp_target = []
    heat_con = []
    heat_gen = []
    tank_con = []
    tank_gen = []
    tot_gen = []
    tot_gen_plus = [] # plusstootlikkus
    tot_gen_minus = [] # miinustootlikkus

    # hetkestaatus andmed
    status = dict()
    t2na_heat = 0
    t2na_tank = 0
    eile_heat = 0
    eile_tank = 0

    # Andmed 12h graafiku jaoks
    for row in logiandmed_dict:

        row_date = datetime.fromtimestamp(int(row) / 1000)
        heat_con_row = logiandmed_dict[row][72]
        tank_con_row = logiandmed_dict[row][78]

        # t2nane summaarne tarbimine
        if (t2na.year, t2na.month, t2na.day) == (row_date.year, row_date.month, row_date.day):
            t2na_heat += float_or_zero(heat_con_row)/60*5 # 5 minuti kaupa andmed
            t2na_tank += float_or_zero(tank_con_row)/60*5 # 5 minuti kaupa andmed
        
        # eilne summaarne tarbimine
        if (eile.year, eile.month, eile.day) == (row_date.year, row_date.month, row_date.day):
            eile_heat += float_or_zero(heat_con_row)/60*5 # 5 minuti kaupa andmed
            eile_tank += float_or_zero(tank_con_row)/60*5 # 5 minuti kaupa andmed

        if row_date >= dateTime_last_hours_fullhour: # andmeread graafiku jaoks
            # kuupäev
            cat_date = round((row_date - dateTime_last_hours_fullhour).seconds / 3600, 2)
            # välistemperatuur
            act_outd_temp.append([cat_date, float_or_none(logiandmed_dict[row][41])])
            # pumpa sisenev ja väljuv temperatuur
            ilet_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][42])])
            olet_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][43])])
            z1_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][44])])
            z2_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][45])])
            z1_water_temp_target.append([cat_date, float_or_none(logiandmed_dict[row][46])])
            z2_water_temp_target.append([cat_date, float_or_none(logiandmed_dict[row][47])])
            tank_temp.append([cat_date, float_or_none(logiandmed_dict[row][40])])
            tank_temp_target.append([cat_date, float_or_none(logiandmed_dict[row][11])])
            heat_con.append([cat_date, float_or_none(heat_con_row)])
            tank_con.append([cat_date, float_or_none(tank_con_row)])
            heat_gen_row = logiandmed_dict[row][74]
            heat_gen.append([cat_date, float_or_none(heat_gen_row)])
            tank_gen_row = logiandmed_dict[row][79]
            tank_gen.append([cat_date, float_or_none(tank_gen_row)])
            # arvutused
            if heat_con_row == None and tank_con_row == None and heat_gen_row == None and tank_gen_row == None:
                tot_gen_row = None
                tot_gen_plus_row = None
            else:
                tot_gen_row = round(float_or_zero(heat_gen_row) + float_or_zero(tank_gen_row), 1)
                tot_gen_plus_row = round(tot_gen_row - (float_or_zero(heat_con_row) + float_or_zero(tank_con_row)), 1)


            tot_gen_plus.append([
                cat_date,
                tot_gen_plus_row if tot_gen_plus_row > 0 else None
            ])
            tot_gen_minus.append([
                cat_date,
                -1 * tot_gen_plus_row if tot_gen_plus_row < 0 else None
            ])
            tot_gen.append([
                cat_date,
                tot_gen_row
            ])
            if verbose:
                print(
                    cat_date,
                    row_date.strftime('%H:%M'),
                    [logiandmed_dict[row][el] for el in elements]
                )
    
    if logiandmed_dict:
        operation_actual['Operation'] = logiandmed_dict[row][0] # Operation [1:Off, 2:On]
        operation_actual['Mode'] = logiandmed_dict[row][2] # Mode [1:Tank, 2:Heat, 3:Cool, 8:Auto, 9:Auto(Heat), 10:Auto(Cool)]
        operation_actual['Tank'] = logiandmed_dict[row][3] # Tank [1:Off, 2:On]
        operation_actual['Zone1-Zone2 On-Off'] = logiandmed_dict[row][4] # Zone1-Zone2 On-Off [1:On-Off, 2:Off-On, 3:On-On]
    
    hist_consum_data = read_aquarea_data_from_pickle()
    kuu_heat = float_or_zero(hist_consum_data['kuu_heat']) + t2na_heat
    kuu_tank = float_or_zero(hist_consum_data['kuu_tank']) + t2na_tank


    status = {
        'datetime': pytz.timezone('Europe/Tallinn').localize(row_date),
        'operation_actual': operation_actual,
        'act_outd_temp': act_outd_temp[-1][1],
        'ilet_water_temp': ilet_water_temp[-1][1],
        'olet_water_temp': olet_water_temp[-1][1],
        'z1_water_temp': z1_water_temp[-1][1],
        'z2_water_temp': z2_water_temp[-1][1],
        'z1_water_temp_target': z1_water_temp_target[-1][1],
        'z2_water_temp_target': z2_water_temp_target[-1][1],
        'tank_temp': tank_temp[-1][1],
        'tank_temp_target': tank_temp_target[-1][1],
        'heat_con_last': heat_con[-1][1],
        'tank_con_last': tank_con[-1][1],
        't2na_heat': t2na_heat,
        't2na_tank': t2na_tank,
        't2na_tot': t2na_heat + t2na_tank,
        'eile_heat': eile_heat,
        'eile_tank': eile_tank,
        'eile_tot': eile_heat + eile_tank,
        'kuu_heat': kuu_heat,
        'kuu_tank': kuu_tank,
        'kuu_tot': kuu_heat + kuu_tank,
        'kuu_eelmine_heat': hist_consum_data['kuu_eelmine_heat'],
        'kuu_eelmine_tank': hist_consum_data['kuu_eelmine_tank'],
        'kuu_eelmine_tot': hist_consum_data['kuu_eelmine_heat'] + hist_consum_data['kuu_eelmine_tank'],
        'kuu_aasta_tagasi_heat': hist_consum_data['kuu_aasta_tagasi_heat'],
        'kuu_aasta_tagasi_tank': hist_consum_data['kuu_aasta_tagasi_tank'],
        'kuu_aasta_tagasi_tot': hist_consum_data['kuu_aasta_tagasi_heat'] + hist_consum_data['kuu_aasta_tagasi_tank'],
        'jooksva_perioodi_heat': hist_consum_data['jooksva_perioodi_heat'] + t2na_heat,
        'jooksva_perioodi_tank': hist_consum_data['jooksva_perioodi_tank'] + t2na_tank,
        'jooksva_perioodi_tot': hist_consum_data['jooksva_perioodi_heat'] + hist_consum_data['jooksva_perioodi_tank'] + t2na_heat + t2na_tank,
        'eelmise_perioodi_heat': hist_consum_data['eelmise_perioodi_heat'],
        'eelmise_perioodi_tank': hist_consum_data['eelmise_perioodi_tank'],
        'eelmise_perioodi_tot': hist_consum_data['eelmise_perioodi_heat'] + hist_consum_data['eelmise_perioodi_tank'],
    }

    chart_data = {
        'act_outd_temp': act_outd_temp,
        'z1_water_temp': z1_water_temp,
        'z2_water_temp': z2_water_temp,
        'heat_con': heat_con,
        'tank_con': tank_con,
        'heat_gen': heat_gen,
        'tank_gen': tank_gen,
        'tot_gen': tot_gen,
        'tot_gen_plus': tot_gen_plus,
        'tot_gen_minus': tot_gen_minus,
        'status': status
    }
    return chart_data

# Tagastab statistilise küttekulu 1h kohta iga täistemperatuuri väärtuse jaoks
def get_con_per_1h(temp=0.0):
    temp = -25.0 if temp < -25.0 else temp
    temp = 20.0 if temp > 20.0 else temp
    with open(settings.STATIC_ROOT / 'app' / 'data' / 'con_per_1h.csv', newline='', ) as csvfile:
        reader = csv.DictReader(csvfile)
        con_per_1h = dict()
        for row in reader:
            con_per_1h[float(row['Actual outdoor temperature [Â°C]'])] = float(row['Heat mode energy consumption mean [kWh]'])
        # print(con_per_1h)
    return con_per_1h[round(temp, 0)]

def read_aquarea_data_from_pickle():
    data_consum = {}
    t2na = datetime.now()
    eile = t2na - timedelta(days=1)
    eile_0hour = datetime(eile.year, eile.month, eile.day, 0)

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    STATIC_ROOT = PurePath.joinpath(BASE_DIR, 'static/')
    failinimi = 'af.pickle'
    failitee = STATIC_ROOT / 'app' / 'data' / failinimi
    with open(failitee, 'rb') as f:
        # The protocol version used is detected automatically, so we do not
        # have to specify it.
        af = pickle.load(f)
    print(af.shape, af.columns)

    # Tarbmine sel kuul
    vahemik = (
        (af.index.year == t2na.year) &
        (af.index.month == t2na.month) # &
        # (af.index < eile_0hour)
    )
    andmed = af[vahemik]
    # print(
    #     andmed.shape,
    #     andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
    #     andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
    # )
    data_consum['kuu_heat'] = andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()
    data_consum['kuu_tank'] = andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()

    # Tarbmine eelmisel aastal samal kuul
    vahemik = (
        (af.index.year == t2na.year-1) &
        (af.index.month == t2na.month)
    )
    andmed = af[vahemik]
    print(
        andmed.shape,
        andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
        andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
    )
    data_consum['kuu_aasta_tagasi_heat'] = andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()
    data_consum['kuu_aasta_tagasi_tank'] = andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()

    # Tarbmine eelmisel kuul
    vahemik = (
        (af.index.year == t2na.year if t2na.month > 2 else t2na.year - 1) &
        (af.index.month == t2na.month - 1 if t2na.month > 2 else 12)
    )
    andmed = af[vahemik]
    print(
        andmed.shape,
        andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
        andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
    )
    data_consum['kuu_eelmine_heat'] = andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()
    data_consum['kuu_eelmine_tank'] = andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()

    # Tarbimine sel perioodil
    vahemik = (
        (af.index < eile_0hour) &
        (af.index >= datetime(t2na.year - 1, 7, 1))
    )
    andmed = af[vahemik]
    print(
        andmed.shape,
        andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
        andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
    )
    data_consum['jooksva_perioodi_heat'] = andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()
    data_consum['jooksva_perioodi_tank'] = andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()

    # Tarbimine eelmisel perioodil
    vahemik = (
        (af.index <= datetime(t2na.year - 1, t2na.month, t2na.day, t2na.hour)) &
        (af.index >= datetime(t2na.year - 2, 7, 1))
    )
    andmed = af[vahemik]
    print(
        andmed.shape,
        andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
        andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum(),
    )
    data_consum['eelmise_perioodi_heat'] = andmed['Heat mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()
    data_consum['eelmise_perioodi_tank'] = andmed['Tank mode energy consumption [kW]'].apply(lambda x: x / 60 * 5).sum()

    return data_consum

def update_db():
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    STATIC_ROOT = PurePath.joinpath(BASE_DIR, 'static/')
    aasta = 2025
    kuu = 5
    p2ev = 1
    kuup2ev = datetime(aasta, kuu, p2ev)
    while kuup2ev < datetime(2025, 5, 3):
        failinimi = f'Statistics_B197792584_raw_{kuup2ev.year}{kuup2ev.month:02d}{kuup2ev.day:02d}.txt'
        failitee = STATIC_ROOT / 'app' / 'data' / failinimi
        if os.path.isfile(failitee):
            data = loe_logiandmed_failist(failitee, verbose=True)
            # pass
        else:
            print(kuup2ev, "puudub")
        kuup2ev += timedelta(days=1)
    
if __name__ == "__main__":
    # data = loe_logiandmed_veebist(hours=12, verbose=True)
    # update_db()
    read_aquarea_data_from_pickle()
    # print(get_con_per_1h(temp=0.0))
