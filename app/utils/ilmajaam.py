# -*- coding: utf-8 -*-
"""
@author: Tõnis Kärdi
@contact: tonis.kardi@kemit.ee
@license: BSD, vt LICENSE faili.
@require: U{lxml<https://pypi.python.org/pypi/lxml>}
@require: U{requests<https://pypi.python.org/pypi/requests>}
@version: 0.1

Riigi Ilmateenistuse vaatlusvõrgu jaamade ja nende asukohtade käšši ehitamine.

Otsitakse muutujas L{stations_filename} määratud faili olemasolu ning
pakutakse selle andmete uuendamist. Andmed salvestatakse GeoJSON formaadis
C{FeatureCollection}ina.

Riigi Ilmateenistuse vaatlusvõrku kuuluvad jaamad päritakse muutujas
L{onet_url} määratud veebilehelt kasutades xpath väljendit L{onet_xpath}.
Jaamade asukohad päritakse ühe kaupa vastavatelt www-külgedelt Riigi
Ilmateenistuse U{kodulehel<http://www.ilmateenistus.ee>}.

Mooduli kasutamiseks:

>>> import ilmajaam

"""

import json
import os
import requests
from lxml import html
from urllib.parse import urlparse

stations_filename = 'andmed/ilmajaam.json'
obs_filename = 'andmed/mootmised.json'
onet_url = 'http://www.ilmateenistus.ee/ilmateenistus/vaatlusvork/'
onet_xpath = '//div[@id="observation-network"]/a'
glink_xpath = '//div[@class="station_google_link"]/a'

def cache_stations(path):
    """Pärib kokku jaamade andmed ja salvestab need kohalikule kettale.

    Jaamade andmed salvestatakse GeoJSON formaadis C{FeatureCollection}ina, 
    U{spetsifikatsioon<http://geojson.org/geojson-spec.html>}. Iga jaama
    kohta, mis lotakse, prinditakse konsooli üks punkt.

    @param path: Rada failini, kuhu jaamade andmed salvestada.
    @type path: C{str}
    """
    stations_cache = []
    for station in get_stations():
        print('.',
        station_url = station.attrib['href'])
        stations_cache.append(
            dict([
                ("geometry", get_location(station_url)),
                ("properties", dict(station.attrib)),
                ("type", "Feature")]))
    feature_collection = dict([
        ("type", "FeatureCollection"),
        ("features", stations_cache)])
    with open(path, 'wb') as f:
        f.write(json.dumps(feature_collection))

def get_location(station_url):
    """Loeb ilmajaama leheküljelt <station_url> selle asukoha.

    >>> stations = ilmajaam.get_stations()    
    >>> station = stations.next()
    >>> location = ilmajaam.get_location(station.attrib['href'])
    >>> location = ilmajaam.get_location(
    ...     'http://example.com') # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: xpath ... ei leidnud googlemapsi linki.
    >>>
    
    @param station_url: URL, millelt lugeda ilmajaama asukoht.
    @type station_url: C{str}
    @return: Ilmajaama asukoha koordinaadid.
    @rtype: C{dict}
    @raise ValueError: Kui xpath ei suuda leida googlemapsi linki.
    """
    x = html.fromstring(open_url(station_url))
    loc = x.xpath(glink_xpath)
    try:
        loc = loc[0]
    except IndexError as ae:
        raise ValueError(
            'xpath %s ei leidnud googlemapsi linki.' % glink_xpath)        
    return parse_gmaps_url(loc.attrib['href'])

def get_stations():
    """Loeb kõikide jaamade andmed vastavalt nende xpathile.

    >>> stations = ilmajaam.get_stations()
    >>> from inspect import isgenerator
    >>> assert isgenerator(stations)
    >>> station = stations.next()
    >>> assert station.attrib.has_key('href')
    >>> assert station.attrib.has_key('data-original-title')

    @return: Vaatlusvõrgu jaama andmed (ilma asukohainfota).
    @rtype: C{generator}"""
    x = html.fromstring(open_url(onet_url))
    stations = x.xpath(onet_xpath)
    for station in stations:
        yield station

def open_url(url, params={}):
    """Avab urli <url> HTTP GET päringuga.

    Päringu parameetrid on esitatud pythoni C{dict}ina. Vaikimisi parameetrid
    puuduvad.
    
    >>> r = ilmajaam.open_url('http://example.com')
    >>> assert r.startswith('<!doctype html>')
    
    @param url: Päritav (resolvable) url, mida saab avada
        HTTP GET meetodil.
    @type url: C{str}
    @return: HTTP GET päringu vastus.
    @param params: HTTP GET päringu parameetrid.
    @type params: C{dict}
    @rtype: C{str}
    """
    try:
        r = requests.get(url, params=params)
        if not r.ok:
            print(r.status_code)
        r.raise_for_status()
        resp = r.text
    except:
        raise
    finally:
        r.close()
    return resp

def parse_gmaps_url(gmaps_url):
    """Parsib googlemaps URLi <gmaps_url> ja loeb sellest viidatud asukoha.

    >>> url = 'https://maps.google.com/?q=-19.2698255,-158.9433132'
    >>> loc = ilmajaam.parse_gmaps_url(url)
    >>> assert loc.has_key('coordinates')
    >>> assert loc.has_key('type')
    >>> assert isinstance(loc['coordinates'], list)
    >>> assert len(loc['coordinates']) == 2
    >>> assert loc['coordinates'] == [-158.9433132, -19.2698255]

    Kontrollime, kas kokkupandud GeoJSON on OK:
    
    >>> import requests
    >>> import json
    >>> r = requests.post('http://geojsonlint.com/validate',
    ...     data=json.dumps(loc))
    >>> r.raise_for_status()
    >>> response = r.json()
    >>> assert response['status'] == 'ok'

    @param gmaps_url: Googlemaps url kujul
        C{https://maps.google.com/?q=-19.2698255,-158.9433132}.
    @type gmaps_url: C{str}
    @return: URLis viidatud asukoht.
    @rtype: C{dict}
    """
    o = urlparse(gmaps_url)
    coords = [float(c) for c in o.query.split('=')[1].split(',')]
    # geojson spec ütleb, et koordinaadid esitatakse easting-northing
    # (s.t lon-lat) jrk, mitte nii nagu gmaps (lat-lon), seega:
    coords.reverse()
    return dict([("coordinates", coords), (("type", "Point"))])

#{ Jooksutab terve protsessi

def run():
    """Jooksutab ilmajaamade käššimise."""
    if not os.path.exists(stations_filename):
        msg = 'Ei leidnud ilmajaamade asukohtade andmeid rajalt'
        k = 'salvestan'
    else:
        msg = 'Leidsin ilmajaamade asukohtade andmed rajalt'
        k = 'uuendan'
    print(msg)
    print( '%s' % os.path.abspath(
        os.path.join(os.path.curdir, stations_filename)))
    c = raw_input('Kas %s (J/E)?' % k)
    if c.lower() == 'j':
        cache_stations(stations_filename)


if __name__ == '__main__':
    # see osa koodist käivitub, kui mooodul panna tööle käsurealt
    # (topeltklõps, must aken, IDLE's F5 vms)
    run()
