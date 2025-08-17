# from bs4 import BeautifulSoup
import datetime
import requests
import urllib3

try:
    from django.conf import settings
    VALGAVESI_USERNAME = settings.VALGAVESI_USERNAME
    VALGAVESI_PASSWORD = settings.VALGAVESI_PASSWORD
    VALGAVESI_MOOTURI_NR = settings.VALGAVESI_MOOTURI_NR
except:
    import dev_conf
    VALGAVESI_USERNAME = dev_conf.VALGAVESI_USERNAME
    VALGAVESI_PASSWORD = dev_conf.VALGAVESI_PASSWORD
    VALGAVESI_MOOTURI_NR = dev_conf.VALGAVESI_MOOTURI_NR



# Vaigistame ssl veateated
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
LOGINURL = 'https://valgavesi.ee/get/data?item=valgaVesiLogin&action=login'
REQUESTURL = 'https://valgavesi.ee/iseteenindus/mooturid'
DATAURL = f'https://valgavesi.ee/iseteenindus/naidud/{VALGAVESI_MOOTURI_NR}'
CSVURL = "https://valgavesi.ee/get/data"
LOGOUTURL = 'https://valgavesi.ee/iseteenindus/logi-valja'

LOGINDATA = {
    'email': VALGAVESI_USERNAME,
    'password': VALGAVESI_PASSWORD,
    'login': 'login'
    }

def login():
    start = requests.get(LOGINURL)

    PHPSESSID = start.cookies['PHPSESSID']
    headers = {'Cookie': f'PHPSESSID={PHPSESSID}'}
    login = requests.post(LOGINURL, data=LOGINDATA, headers=headers)

    result = requests.get(REQUESTURL, headers=headers)
    print('Kontroll:', result.status_code, result.text.find('Sulevi'))
    return headers

def get_csvdata(headers):
    today = datetime.date.today()

    csv_params = {
        'item': 'valgaVesiBills',
        'action': 'csv',
        'gauge': VALGAVESI_MOOTURI_NR,
        'start': '2016-01-01',
        'end': f'{today}',
        }
    csv_resp = requests.get(
        CSVURL,
        params=csv_params,
        headers=headers
        )
    return csv_resp

def save_consum(csv_resp):
    content = csv_resp.content
    csv_filename = csv_resp.headers['Content-Disposition'].split('=')[1].replace('"', '')
    print(len(content), csv_filename)
    with open(csv_filename, 'wb') as f:
        f.write(content)
    return csv_filename
    
def show_consum(csv_resp, months=3):
    rows = csv_resp.text.split('\n')
    summa = 0
    for row in range(1, months+1):
        kuup2ev, kogus = rows[row].split(';')[:2]
        summa += float(kogus)
        print(kuup2ev, kogus)
    print('Kokku:', round(summa, 3))
    
def logout(headers):
    out = requests.get(
        LOGOUTURL,
        headers=headers
        )
    return out

if __name__ == '__main__':
    headers = login()
    csv_resp = get_csvdata(headers)
    # save_consum(csv_resp)
    show_consum(csv_resp, months=3)
    logout(headers)
