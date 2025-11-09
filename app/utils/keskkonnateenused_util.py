import requests
from dev_conf import KKT_LEPINGUD

LEPINGUD = KKT_LEPINGUD

# BASE_URL = 'https://www.keskkonnateenused.ee/customer-support/next-shipping-day?contractNumber='
API_URL = "https://cms.keskkonnateenused.ee/wp-json/general-purpose-api/upcoming-discharges"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
# hangib Keskkonnateenuse veebist järgmise veopäeva
def get_next_servicedata(leping):
    payload = {'contractNumber': leping}
    r = requests.get(API_URL, params=payload)
    if r.status_code == 200:
        return r.json()
    else:
        return None
    
def get_tyhjendused():
    tyhjendused = []
    for aadress in LEPINGUD.keys():
        leping = LEPINGUD[aadress]
        data = get_next_servicedata(leping)
        if data:
            for tyhjendus in data:
                tyhjendused.append(
                    {
                        'aadress': aadress,
                        'date': tyhjendus['date'],
                        'garbage': tyhjendus['garbage'],
                        'itemType': tyhjendus['itemType']
                    }
                )
    return tyhjendused
    
if __name__ == "__main__":
    tyhjendused = get_tyhjendused()
    for tyhjendus in sorted(tyhjendused, key=lambda tyhjendus: tyhjendus['date']):
        print(tyhjendus['aadress'], tyhjendus['date'], tyhjendus['garbage'], tyhjendus['itemType'])