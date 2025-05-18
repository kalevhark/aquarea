import csv
from datetime import datetime, timedelta
import os
import sys
import time

import requests

import ilmajaam
import ilmajaam_mootmine

def main(path, ykstund = False, aasta = 2019, kuu = 12, paev = 1, tund = 0):
    # Vanimad andmed on alates 30.01.2004
    # ykstund = True : Kui on vaja ainult ühe tunni andmeid

    # Ilmateenistuse andmebaasi viited
    obs_history_url = \
        'https://www.ilmateenistus.ee/ilm/ilmavaatlused/vaatlusandmed/tunniandmed/'

    # Kontrollime kui kiiresti võib krabada andmeid
    robots_url = 'http://www.ilmateenistus.ee/robots.txt'
    try:
        delay = 1
        response = requests.get(robots_url)
        if response.ok:
            read = response.text.split('\n')
            for rida in read:
                if 'delay' in rida:
                    delay = int(rida.split(':')[1])
    except:
        delay = 30
    print(f'Veebilehe andmete krabamise poliitika: {delay}s')
                    
    # Sisendandmed
    jaam = 'Valga'
    algus = datetime(aasta, kuu, paev, tund) # Millisest ajahetkest alata

    # Väljundfaili nime konstrueerimine
    if paev !=1 or tund !=0:
        timestamp = '_' + str(paev).zfill(2) + str(tund).zfill(2)
    else:
        timestamp = ''
    failinimi = os.path.join(
        path,
        ''.join([
            'Ilmateenistus_',
            jaam,
            str(aasta),
            str(kuu).zfill(2),
            timestamp,
            '.csv'
            ]
        )
    )

    with open(failinimi, 'w', newline='', encoding='utf8') as csvfile:
        while algus.month == kuu: # Kuni kuu lõpuni, (algus.year = aasta): aasta lõpuni

            # Moodustamine päringustringi
            date = algus.strftime("%d.%m.%Y")
            hour = algus.strftime("%H")
            params = {'filter[date]' : date, 'filter[hour]' : hour}

            # Küsime andmed veebist
            retrys = 10
            while retrys > 0:
                r = requests.get(obs_history_url, params=params)
                if r.ok:
                    response = r.text
                    r.close()
                    break
                else:
                    retrys -= 1
                    print(f'{r.status_code}: {retrys} korda jäänud veel proovida, paus {10*delay}s...')
                    r.close()
                    time.sleep(10*delay)
                    # r.raise_for_status()
                    # raise

            # Töötleme andmed
            x = ilmajaam.html.fromstring(response)
            xtab = x.xpath('//table')[0]
            date = x.xpath('//input[@name="filter[date]"]')[0].attrib.get('value')
            hour = x.xpath('//input[@name="filter[hour]"]')[0].attrib.get('value')
            
            keys = ilmajaam_mootmine.get_past_obs_keys(xtab.xpath('thead')[0]) # Loeme ilmaandmete veerunimed
            date = datetime.strptime(date, '%d.%m.%Y').strftime('%Y-%m-%d')
            obs = ilmajaam_mootmine.parse_past_observations(xtab, keys, '%s %s:00:00' %(date, hour))
            if algus.month == kuu and algus.day == paev and algus.hour == tund: # esimene kord vaja
                writer = csv.DictWriter(csvfile, fieldnames=keys+['timestamp'])
                writer.writeheader()
            writer.writerow(obs[jaam])

            print(
                algus.strftime("%d.%m.%Y"),
                f'{algus.hour:>2}',
                f'{obs[jaam]["Õhutemperatuur (°C)"]}'
            )
            algus += timedelta(hours=1)
            time.sleep(delay) # Teeme pausi, et veeb ei lükkaks päringuid tagasi
            if ykstund:
                break

if __name__ == "__main__":
    # execute only if run as a script
    date_list = [2020, 5, 25, 16]
    path = os.path.dirname(sys.argv[0])
    if len(sys.argv) < 2:
        print(f'Kasutame vaikimisi määratud kuupäeva {datetime(*date_list).strftime("%d.%m.%Y")}')
    else:
        date_list = [int(el) for el in sys.argv[1].split('_') if el]
        try:
            ref_kuup2ev = datetime(*date_list)
            print(f'Kasutame määratud aega {datetime(*date_list).strftime("%d.%m.%Y")}')
        except:
            print(f'Kasutame tänast kuupäeva {datetime(*date_list).strftime("%d.%m.%Y")}')
    # Käivitame põhiprotsessi        
    main(path, False, *date_list)
