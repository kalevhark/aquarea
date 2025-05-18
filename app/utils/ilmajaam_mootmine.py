# -*- coding: utf-8 -*-
"""
@author: Tõnis Kärdi
@contact: tonis.kardi@kemit.ee
@license: BSD, vt LICENSE faili.
@version: 0.1

Riigi Ilmateenistuse vaatlusvõrgu jaamade viimaste vaatlusandmete käššimine
ja andmete (viimane automaatjaamade seis ning tunni kaupa ajalugu) pärimine.

Viimaste vaatluste andmed laetakse alla  muutujas L{obs_url} määratud URLilt
XML formaadis. Kuna puudub parem sidumisviis mõõtmiste ja mõõtmisi teostanud
jaama vahel, kasutame sidumiseks jaamade nimetusi. Kahjuks need küll nende
kahe andmehulga vahel ei ühti, nt
    - Tartu (Kvissentali) hüdromeetriajaam ja Tartu-Kvissental
    - Haapsalu meteoroloogiajaam, Haapsalu rannikujaam ja
        Haapsalu, Haapsalu sadam.
Kuid me ei lase end sellest väga morjendada, mis nime alusel suudame kokku
panna, selle paneme. Mõte selles, et see on ainult näide ju tegelikult, mitte
elukriitiline süsteem :)

Käsurealt käivitades salvestatakse viimaste vaatluste andmed GeoJSON
formaadis C{FeatureCollection}ina muutujas L{ilmajaam.obs_filename}
määratud faili (vana sisu kirjutatakse alati üle).

Ajaloolised andmed päritakse muutujas L{obs_history_url} määratud URLilt
HTML <tabel>ina, mis siis töödeldakse ümber. Jaamade ja mõõtmisandmete sidumine
toimub samadel alustel (sama meetodiga) nagu ka viimaste vaatluste andmete
puhul.

Ajalooliste andmete pärimisel saab parameetrina kaasa anda, mis konkreetse
kuupäeva ja tunni andmeid vaja on - vaikimisi tagastatakse ajaliselt viimased
andmed, mis olemas. 

Mooduli kasutamiseks:

>>> import ilmajaam_mootmine

"""

import datetime
import ilmajaam

obs_url = 'http://www.ilmateenistus.ee/ilma_andmed/xml/observations.php'
obs_xpath = '//observations/station'
obs_history_url = \
    'http://www.ilmateenistus.ee/ilm/ilmavaatlused/vaatlusandmed/tunniandmed/'
skipchars = '()- '
stations_fc = None

#{ Automaatjaamade hetkeseis

def get_obs():
    """Tagastab viimaste mõõtmiste andmed.

    @return: Viimased mõõtmised Riigi Ilmateenistuse www-küljelt,
        mis on määratud muutujas L{obs_url} ja seotud neid teostanud
        vaatlusvõrgu jaamade asukohtadega. Vastus tagastatakse GeoJSON
        C{FeaturCollection}ina.
    @rtype: C{dict}
    """
    return merge_obs_sts(get_observations())

def get_observations():
    """Pärib viimaste vaatluste andmed.

    Andmed päritakse muutujas L{obs_url} määratud asukohast ja loetakse
    sisse XMLina. See XML teisendatakse jaama kaupa pythoni C{dict}iks,
    kus võtmena kasutusel jaama nimi.

    >>> observations = ilmajaam_mootmine.get_observations()
    >>> assert isinstance(observations, dict)
    >>> assert len(observations.keys()) > 0
    >>> assert u'Tartu-T\u00f5ravere' in observations.keys()
    
    @return: Viimaste vaatluste andmed.
    @rtype: C{dict}
    """
    obs = {}
    x = ilmajaam.html.fragments_fromstring(ilmajaam.open_url(obs_url))[1]
    ts = datetime.datetime.fromtimestamp(
        float(x.attrib['timestamp'])).strftime('%d-%m-%Y %H:%M:%S')
    for station in x.xpath(obs_xpath):
        station_name = station.xpath('name')[0].text
        obs[station_name] = dict(
            [(n.tag, _try_convert(n.text)) for n in station.iterchildren()])
        obs[station_name]['timestamp'] = ts
    return obs

def get_stations():
    """Tagastab vaatlusvõrgu jaamade asukohtade GeoJSONi.

    Andmed laetakse muutujas L{ilmajaam.stations_filename} määratud
    asukohast. Fail peab olema olemas ja õiges struktuuris (ei kontrollita).

    @return: Vaatlusvõrgu jaamade asukohtade GeoJSON.
    @rtype: C{dict}
    """
    with open(ilmajaam.stations_filename) as _f:
        f = _f.read()
    return ilmajaam.json.loads(f)    

def loop_stations(stations_fc):
    """Iteraator üle käššitud vaatlusvõrgu jaamade asukohtade.

    @param stations_fc: Vaatlusvõrgu jaamade asukohad GeoJSON
        C{FeatureCollection}ina.
    @type stations_fc: C{dict}
    @return: Vaatlusvõrgu jaamad.
    @rtype: C{generator}
    """
    for f in stations_fc['features']:
        yield f

#{ Ajaloolised andmed

def get_past_obs_keys(thead):
    """Teisendab HTML <thead> elemendi "veeru päisteks".

    See meetod on kogu protsessi kõige nõrgem lüli hetkel. Kui peaks muutuma
    tunniandmete tabeli struktuur, siis on suure tõenäosusega andmete
    teisendus katki.

    @param thead: Teisendatav HTML <thead> element.
    @type thead: C{lxml.html.HtmlElement}
    @return: Veergude päised.
    @rtype: C{list}
    """
    keys = []
    trs = thead.xpath('tr')
    for th in trs[0].xpath('th'):
        _keys = []
        if th.attrib.get('rowspan', '0') >= '%i' % len(trs):
            key = th.text
        if th.attrib.get('colspan', '0') >= '2':
            key = th.text
            for th2 in thead.xpath('tr')[1].xpath('th'):
                _keys.append('%s %s' %(key, th2.text))
        else:
            _keys.append(key)
        if len(_keys) > 0:
            keys.extend(_keys)
    return keys

def get_past_obs(date=None, hour=None):
    """Pärib ja tagastab vaatlusvõrgu tunniandmed soovitud ajast.

    @param date: Soovitud kuupäev kujul C{PP.KK.AAAA}. Vaikimisi
        C{None} - tähistab tänast kuupäeva
    @type date: C{str}
    @param hour: Soovitud täistund kujul C{HH} (24h kell). Vaikimisi
        C{None} - tähistab praegust viimast täistundi.
    @type hour: C{str}
    @return: Soovitud aja vaatlusvõrgu tunniandmed GeoJSON formaadis
        C{FeatureCollection}ina.
    @rtype: C{dict}
    """
    date = date or datetime.datetime.now().strftime("%d.%m.%Y")
    hour = hour or datetime.datetime.now().strftime("%H") 
    params = {'filter[date]' : date, 'filter[hour]' : hour}
    x = ilmajaam.html.fromstring(
        ilmajaam.open_url(obs_history_url, params=params))
    xtab = x.xpath('//table')[0]
    date = x.xpath('//input[@name="filter[date]"]')[0].attrib.get('value')
    hour = x.xpath('//input[@name="filter[hour]"]')[0].attrib.get('value')
    keys = get_past_obs_keys(xtab.xpath('thead')[0])
    obs = parse_past_observations(xtab, keys, '%s %s:00:00' %(date, hour))
    return merge_obs_sts(obs)

def parse_past_observations(x, keys, ts):
    """Teisendab HTMLis esitatud tunniandmete tabeli.

    @param x: Vaatlusvõrgu tunniandmete HTML <table> element Riigi
        Ilmateenistuse www-küljelt, mis on määratud muutujaga
        L{obs_history_url}.
    @type x: C{lxml.html.HtmlElement}
    @param keys: Veerud, mida hakkame antud tabelist otsima.
    @type keys: C{list}
    @param ts: Ajatempel, mis näitab, mis hetke mõõtmisega on tegu. See
        lisatakse iga vaatlusrea juurde.
    @type ts: C{str}
    @return: Sissetulnud HTMList loetud vaatlusvõrgu tunniandmed.
    @rtype: C{dict}
    """
    obs = {}
    for station in x.xpath('tbody/tr'):
        station_name = station.xpath('td')[0].text
        obs[station_name] = dict(
            zip([key for key in keys],
                [_try_convert(n.text) for n in station.iterchildren()]))
        obs[station_name]['timestamp'] = ts
    return obs  
    
#{ Üldine

def merge_obs_sts(obs):
    """Liidab omavahel kokku jaamade ja mõõtmiste andmed.

    Vaatlusvõrgu jaama ja konkreetse mõõtmise omavaheliseks sidumiseks
    püüame omavahel kokku ajada kummaski andmekogus esitatud jaamade
    nimetused.

    @param obs: Ilmavaatluste andmed
    @type obs: C{dict}
    """
    stations_fc = get_stations()
    station_names = obs.keys()
    station_names.sort()
    stations = loop_stations(stations_fc)
    station = {}
    for station_name in station_names:
        _station_name = station_name.split(' ')[0]
        match = False
        while not match:
            station_title = station.get(
                'properties', {}).get('data-original-title', '')
            if ''.join([n for n in station_title if n not in skipchars]) == \
                 ''.join([n for n in station_name if n not in skipchars]):
                match = True
            elif station_title.startswith(_station_name) and \
                 station_title != '':
                match = True
            if match == True:
                station['properties'].update(obs[station_name])
            elif station_title > _station_name:
                match = True
            else:                
                station = stations.next()
    return stations_fc

def _try_convert(val):
    """Püüab koverteerida sissetulnud väärtust numbriliseks.

    >>> i = ilmajaam_mootmine._try_convert('123')
    >>> assert isinstance(i, int) and i == 123
    >>> i = ilmajaam_mootmine._try_convert('123.4')
    >>> assert isinstance(i, float) and i == 123.4

    NB! komakoha eraldajaks võib olla ka koma:

    >>> i = ilmajaam_mootmine._try_convert('123,4')
    >>> assert isinstance(i, float) and i == 123.4    

    Kui väärtuse konverteerimine peaks ebaõnnestuma, siis tagastatakse
    algne sisendparameeter:
    
    >>> i = ilmajaam_mootmine._try_convert('foobar')
    >>> assert isinstance(i, str) and i == 'foobar'

    @param val: Konverteeritav väärtus.
    @return: Numbriliseks konverteeritud väärtus või
        algne väärtus kui konversioon ei õnnestunud.
    @rtype: C{int} or C{float}"""
    try:
        assert val != None
        val = val.strip()
        if val == '':
            val = None
        assert val != None
        val = _try_type(val, int)
        if not isinstance(val, int):
            val = _try_type(val.replace(',','.'), float)
    except AssertionError as ae:
        pass
    return val

def _try_type(val, _type):
    """Püüab konverteerida väärtust mingisse andmetüüpi.

    >>> i = ilmajaam_mootmine._try_type('123', int)
    >>> assert isinstance(i, int) and i == 123
    >>> i = ilmajaam_mootmine._try_type('123.4', float)
    >>> assert isinstance(i, float) and i == 123.4

    Kui väärtuse konverteerimine peaks ebaõnnestuma, siis tagastatakse
    algne sisendparameeter:
    
    >>> i = ilmajaam_mootmine._try_type('foobar', int)
    >>> assert isinstance(i, str) and i == 'foobar'
    
    @param val: Väärtus, mida muuta.
    @type val: C{any}
    @param _type: Tüüp, millesse püüda väärtust konverteerida.
    @type _type: C{type}
    @return: Konverteeritud väärtus. Juhul kui teisendus ebaõnnestub,
        siis algne sisendväärtus.
    @rtype: C{any}
    """
    try:
        assert val != None
        val = _type(val)
    except:
        pass
    return val


if __name__ == '__main__':
    # kui käivitame käsurealt, siis salvestame viimaste
    # mõõtmiste andmed kohalikule kettale.
    ilmajaam.run()
    stations_fc = get_obs()
    with open(ilmajaam.obs_filename, 'wb') as _f:
        _f.write(ilmajaam.json.dumps(stations_fc))
