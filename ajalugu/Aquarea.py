from datetime import datetime, timedelta
import os
import pickle

import pandas as pd
import pytz

from django.conf import settings

try:
    DATA_DIR = os.path.join(settings.STATIC_ROOT, 'ajalugu/data/')
except:
    DATA_DIR = os.path.join(os.getcwd(), 'static/ajalugu/data/')

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def nulliga(number):
    return str("{0:02d}").format(number)

def soodus(aeg):
    tz = pytz.timezone('Europe/Tallinn')
    aeg = aeg.replace(tzinfo=tz)
    if aeg.weekday() > 4: # 5-laupäev, 6-pühapäev
        return True
    if aeg.dst():
        if aeg.hour < 8:
            return True
    else:
        if aeg.hour < 7 or aeg.hour >= 23:
            return True
    return False


class EEYldHindData():
    '''Andmed EE ja EL üldteenuse hinnaajaloost ja nende töötlused'''    
    
    def __init__(self):
        print('EE/EL ', end='')
        bd_DATA_DIR = DATA_DIR + 'bdy/'
        ajf = []
        with os.scandir(bd_DATA_DIR) as it:
            for entry in it:
                if entry.name.startswith(
                        'EE_yldhind') and entry.is_file():  # Loeme ainult Aquarea logifailid andmefreimidesse
                    fail = bd_DATA_DIR + entry.name
                    print('Loeme faili: ', fail)
                    ajf.append(pd.read_csv(fail, skiprows=1, delimiter=';', decimal=','))
        self.af = pd.concat(ajf[:], axis=0).drop_duplicates() # Ühendame andmefreimid ja kõrvaldame duplikaadid
        self.af['Aeg'] = self.af['Aasta'].apply(str) + self.af['Kuu'].apply(nulliga)
        self.af = self.af.set_index('Aeg')
                
    def __repr__(self):
        tekst = 'Andmeridu:' + str(self.af.shape[0]) + ':'
        for i in range(len(self.af.columns)):
            tekst += '\n'+'{0:02d}. {1}'.format(i, self.af.columns[i])        
        return tekst
    
    def __str__(self):
        
        algus_aasta = self.af['Aasta'].min()
        algus_kuu = self.af['Kuu'][self.af['Aasta'] == algus_aasta].min()
        l6pp_aasta = self.af['Aasta'].max()
        l6pp_kuu = self.af['Kuu'][self.af['Aasta'] == l6pp_aasta].max()
        tekst = 'EE hinnaajaloo andmed: ' + str(algus_aasta) + '-' + str(algus_kuu) + ' - ' + str(l6pp_aasta) + '-' + str(l6pp_kuu) + ' Andmeridu:' + str(self.af.shape[0])
        return tekst
    
    def v(self,veerg=0):
        '''Veerunimede viitamise lühendamiseks self.af.columns[n] -> v(n)'''
        self.veerg = veerg
        return self.af.columns[veerg]

    def EEhind(self, aeg=datetime.today()):
        aeg = datetime(*aeg)
        aastakuu = "{0:04d}{1:02d}".format(aeg.year, aeg.month)
        if aastakuu in self.af.index:
            if soodus(aeg):
                return self.af['EE_Soodus'][aastakuu]
            else:
                return self.af['EE_Normaal'][aastakuu]
        else:
            return 0 # perioodi EE üldhind ei ole teada

    def ELhind(self, aeg=datetime.today()):
        aeg = datetime(*aeg)
        aastakuu = "{0:04d}{1:02d}".format(aeg.year, aeg.month)
        if aastakuu in self.af.index:
            if soodus(aeg):
                return self.af['EL_Soodus'][aastakuu]
            else:
                return self.af['EL_Normaal'][aastakuu]
        else:
            return 0 # perioodi EL üldhind ei ole teada

    def kuudeandmed(self, **kwargs):
        '''Andmed tunnikaupa grupeerituna soovitud perioodiks (start=dt, stopp=dt)'''
        self.start = self.af.index.min()
        self.stopp = self.af.index.max()

        if kwargs:
            if 'start' in kwargs:
                self.start = f'{kwargs["start"].year}{kwargs["start"].month:02d}'

            if 'stopp' in kwargs:
                self.stopp = f'{kwargs["stopp"].year}{kwargs["stopp"].month:02d}'

        # defineerime otsitava vahemiku
        vahemik = (
                (self.af.index >= self.start) &
                (self.af.index <= self.stopp)
        )
        andmed = self.af[vahemik]
        return andmed

class AquareaData():
    '''Andmed Aquarea Service Cloud andmelogist ja nende töötlused'''    
    
    def __init__(self):
        print('Aquarea ', end='')
        bd_DATA_DIR = DATA_DIR+'bda/'
        if os.path.isfile(bd_DATA_DIR + 'af.pickle'):
            algus = datetime.now()
            with open(bd_DATA_DIR + 'af.pickle', 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
            aeg = datetime.now() - algus
            print(f'pickle: {aeg.seconds}.{aeg.microseconds}s')
        else:
            algus = datetime.now()
            ajf = []
            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    if entry.name.startswith('Statistics_B197792584') and entry.is_file(): # Loeme ainult Aquarea logifailid andmefreimidesse
                        fail = bd_DATA_DIR + entry.name
                        print('Loeme faili: ', fail)
                        ajf.append(pd.read_csv(fail, delimiter=',', decimal='.', parse_dates=[0],
                                 usecols=[0,1,3,8,9,12,13,17,19,20,21,22,25,32,34,35,36,37,38,40,42,45,47,49,50,51,57,58,59,66,67,70,71],))

            print('Liidame andmed ja kõrvaldame duplikaadid...')
            self.af = pd.concat(ajf[:], axis=0).drop_duplicates() # Ühendame andmefreimid ja kõrvaldame duplikaadid
            self.af = self.af.set_index('Timestamp')

            # Kirjutame andmed pickle faili
            with open(bd_DATA_DIR + 'af.pickle', 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.HIGHEST_PROTOCOL)
            aeg = datetime.now() - algus
            print(f'files: {aeg.seconds}.{aeg.microseconds}s')

    def __repr__(self):
        tekst = 'Andmeridu:' + str(self.af.shape[0]) + ':'
        for i in range(len(self.af.columns)):
            tekst += '\n'+'{0:02d}. {1}'.format(i, self.af.columns[i])        
        return tekst
    
    def __str__(self):
        algus = self.af.index.min().strftime('%d.%m.%Y %H:%M')
        l6pp = self.af.index.max().strftime('%d.%m.%Y %H:%M')
        tekst = 'Aquarea andmed: ' + algus + '-' + l6pp + ' Andmeridu:' + str(self.af.shape[0])
        return tekst
    
    def v(self,veerg=0):
        '''Veerunimede viitamise lühendamiseks self.af.columns[n] -> v(n)'''
        self.veerg = veerg
        return self.af.columns[veerg]
    
    def tunniandmed(self, **kwargs):
        '''Andmed tunnikaupa grupeerituna soovitud perioodiks (start=dt, stopp=dt)'''
        self.start = self.af.index.min()
        self.stopp = self.af.index.max()
       
        if kwargs:
            if 'start' in kwargs:
                self.start = kwargs['start']
                
            if 'stopp' in kwargs:
                self.stopp = kwargs['stopp'] + timedelta(days=1) # .replace(minute=0, second=0, microsecond=0)
        
        # defineerime otsitava vahemiku
        vahemik = (
            (self.af.index >= self.start) &
            (self.af.index < self.stopp)
        )
        andmed = self.af[vahemik]
        
        # grupeerime aasta, kuu, päeva ja tunni kaupa
        levels = [
            andmed.index.year,
            andmed.index.month,
            andmed.index.day,
            andmed.index.hour
        ]
        cols = [self.v(i) for i in (12, 13, 14, 28, 30, 29, 31)]
        return andmed.groupby(levels).mean()[cols]


    def cop(self, **kwargs):
        """
        Kasutegur kuude kaupa grupeerituna soovitud perioodiks (start, stopp)
        Kasutamine näiteks:
        bda.cop(start=datetime(2018, 9, 22))['months']
        bda.cop(start=datetime(2018, 9, 22))['days'].loc[(2018, 12)]
        """
        
        self.start = self.af.index.min()
        self.stopp = self.af.index.max()
        
        if kwargs is not None:
            if 'start' in kwargs:
                self.start = kwargs['start']
                
            if 'stopp' in kwargs:
                self.stopp = kwargs['stopp'] + timedelta(days=1) # .replace(minute=0, second=0, microsecond=0)

        # Valime ainult soovitud kuupäevavahemiku
        df = self.p2evaandmed(start=self.start, stopp=self.stopp)
        # Anname tulpadele lühemad pealkirjad
        df.columns = ['temp_heat', 'temp_tank', 'temp_out', 'con_heat', 'con_tank', 'gen_heat', 'gen_tank']
        sel_cols = ['con_heat', 'con_tank', 'gen_heat', 'gen_tank']
        # Perioodi andmed kokku
        df_period = df[sel_cols].sum()
        cop_period = df_period['gen_heat'] / df_period['con_heat']
        # Perioodi andmed kuude kaupa
        df_months = df[sel_cols].groupby([df.index.year, df.index.month]).sum()
        cop_months = df_months['gen_heat'] / df_months['con_heat']
        # Perioodi andmed päevade kaupa
        df_days = df[sel_cols].groupby([df.index.year, df.index.month, df.index.day]).sum()
        cop_days = df_days['gen_heat'] / df_days['con_heat']
        # Loome sõnastiku
        andmed = {
            'period': cop_period,
            'months': cop_months,
            'days': cop_days
        }
        return andmed


class ElektrileviData():
    '''Andmed Elektrilevi andmebaasist ja nende töötlused'''   
    
    def __init__(self):
        print('Elektrilevi ', end='')
        bd_DATA_DIR = DATA_DIR + 'bde/'
        if os.path.isfile(bd_DATA_DIR + 'af.pickle'):
            algus = datetime.now()
            with open(bd_DATA_DIR + 'af.pickle', 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
            aeg = datetime.now() - algus
            print(f'pickle: {aeg.seconds}.{aeg.microseconds}s')
        else:
            algus = datetime.now()
            ajf = []
            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    if entry.name.startswith(
                            'Elektrilevi_S9a') and entry.is_file():  # Loeme ainult Elektrilevi logifailid andmefreimidesse
                        fail = bd_DATA_DIR + entry.name
                        print('Loeme faili: ', fail)
                        ajf.append(pd.read_csv(fail, delimiter=';',
                                 skiprows=6, header=None, names = ['Timestamp','Elektrienergia kulu [kWh]'], # Jätame ära algusread ja nimetame ise veerud
                                 parse_dates=[0], dayfirst = True, # Konverteerime 1. veeru Euroopa kuupäevatüüpi
                                 decimal = ',', # Murdosa eraldajaks on koma
                                 usecols=[0,2]).dropna(how='any')) # Loeme ainult täielike andmetega veerud Algusaeg, Lõppaeg ja Kogus
            self.af = pd.concat(ajf[:], axis=0).drop_duplicates() # Ühendame andmefreimid ja kõrvaldame duplikaadid
            self.af = self.af.set_index('Timestamp')

            # Kirjutame andmed pickle faili
            with open(bd_DATA_DIR + 'af.pickle', 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.HIGHEST_PROTOCOL)
            aeg = datetime.now() - algus
            print(f'files: {aeg.seconds}.{aeg.microseconds}s')

    def __repr__(self):
        tekst = 'Andmeridu:' + str(self.af.shape[0]) + ':'
        for i in range(len(self.af.columns)):
            tekst += '\n'+'{0:02d}. {1}'.format(i, self.af.columns[i])        
        return tekst
    

    def __str__(self):
        algus = self.af.index.min().strftime('%d.%m.%Y %H:%M')
        l6pp = self.af.index.max().strftime('%d.%m.%Y %H:%M')
        tekst = 'Elektrilevi andmed: ' + algus + '-' + l6pp + ' Andmeridu:' + str(self.af.shape[0])
        return tekst
    
    def v(self,veerg=0):
        '''Abifunktsioon veerunimede viitamise lühendamiseks self.af.columns[n] -> v(n)'''
        self.veerg = veerg
        return self.af.columns[veerg]
    
    def tunniandmed(self, **kwargs):
        '''Andmed soovitud perioodiks (start, stopp)'''
        self.start = self.af.index.min()
        self.stopp = self.af.index.max()
        
        if kwargs:
            if 'start' in kwargs:
                self.start = kwargs['start']
                
            if 'stopp' in kwargs:
                self.stopp = kwargs['stopp'] + timedelta(days=1) # .replace(minute=0, second=0, microsecond=0)

        # defineerime otsitava vahemiku
        vahemik = (
            (self.af.index >= self.start) &
            (self.af.index < self.stopp)
        )
        andmed = self.af[vahemik]
        
        # grupeerime aasta, kuu, päeva ja tunni kaupa
        levels = [
            andmed.index.year,
            andmed.index.month,
            andmed.index.day,
            andmed.index.hour
        ]
        return andmed.groupby(levels).mean()
        

class IlmateenistusData():
    '''Andmed Elektrilevi andmebaasist ja nende töötlused'''
    
    def __init__(self):
        print('Ilmateenistus ', end='')
        bd_DATA_DIR = DATA_DIR + 'bdi/'
        if os.path.isfile(bd_DATA_DIR + 'af.pickle'):
            algus = datetime.now()
            with open(bd_DATA_DIR + 'af.pickle', 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
            aeg = datetime.now() - algus
            print(f'pickle: {aeg.seconds}.{aeg.microseconds}s')
        else:
            algus = datetime.now()
            ajf = []
            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    if entry.name.startswith(
                            'Ilmateenistus_Valga') and entry.is_file():  # Loeme ainult Elektrilevi logifailid andmefreimidesse
                        fail = bd_DATA_DIR + entry.name
                        print('Loeme faili: ', fail)
                        ajf.append(pd.read_csv(fail, delimiter=',',
                            skiprows=1, header=None, decimal = '.',
                            usecols=[1,2,3,6,11,13],
                            names = ['Ametlik mõõdetud temperatuur [°C]', 'Niiskus', 'Õhurõhk', 'Tuul', 'Sademed', 'Timestamp'], # Kasutame osa veerge ja paneme nimed
                            parse_dates=[5]))
            self.af = pd.concat(ajf[:], axis=0).drop_duplicates() # Ühendame andmefreimid ja kõrvaldame duplikaadid
            self.af = self.af.set_index('Timestamp')

            # Kirjutame andmed pickle faili
            with open(bd_DATA_DIR + 'af.pickle', 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.HIGHEST_PROTOCOL)
            aeg = datetime.now() - algus
            print(f'files: {aeg.seconds}.{aeg.microseconds}s')

    def __repr__(self):
        tekst = 'Andmeridu:' + str(self.af.shape[0]) + ':'
        for i in range(len(self.af.columns)):
            tekst += '\n'+'{0:02d}. {1}'.format(i, self.af.columns[i])        
        return tekst
    

    def __str__(self):
        algus = self.af.index.min().strftime('%d.%m.%Y %H:%M')
        l6pp = self.af.index.max().strftime('%d.%m.%Y %H:%M')
        tekst = 'Ilmateenistuse andmed: ' + algus + '-' + l6pp + ' Andmeridu:' + str(self.af.shape[0])
        return tekst
    
    def tunniandmed(self, **kwargs):
        '''Andmed soovitud perioodiks (start, stopp)'''
        
        self.start = self.af.index.min()
        self.stopp = self.af.index.max()
        
        if kwargs:
            if 'start' in kwargs:
                self.start = kwargs['start']
                
            if 'stopp' in kwargs:
                self.stopp = kwargs['stopp'] + timedelta(days=1) # .replace(minute=0, second=0, microsecond=0)

        # defineerime otsitava vahemiku
        vahemik = (
            (self.af.index >= self.start) &
            (self.af.index < self.stopp)
        )
        andmed = self.af[vahemik]
        
        # grupeerime aasta, kuu, päeva ja tunni kaupa
        levels = [
            andmed.index.year,
            andmed.index.month,
            andmed.index.day,
            andmed.index.hour
        ]
        cols = ['Ametlik mõõdetud temperatuur [°C]']
        return andmed.groupby(levels).mean()[cols]


class NordPoolData():
    '''Andmed Elektrilevi https://dashboard.elering.ee/et/nps/price andmebaasist ja nende töötlused'''   
    
    def __init__(self):
        print('NordPool ', end='')
        bd_DATA_DIR = DATA_DIR + 'bdn/'
        if os.path.isfile(bd_DATA_DIR + 'af.pickle'):
            algus = datetime.now()
            with open(bd_DATA_DIR + 'af.pickle', 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
            aeg = datetime.now() - algus
            print(f'pickle: {aeg.seconds}.{aeg.microseconds}s')
        else:
            algus = datetime.now()
            ajf = []
            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    if entry.name.startswith(
                            'nps-export') and entry.is_file():  # Loeme ainult Elektrilevi logifailid andmefreimidesse
                        fail = bd_DATA_DIR + entry.name
                        print('Loeme faili: ', fail)
                        ajf.append(pd.read_csv(fail, delimiter=';',
                                 decimal = ',')) # Murdosa eraldajaks on koma

            self.af = pd.concat(ajf[:], axis=0).drop_duplicates() # Ühendame andmefreimid ja kõrvaldame duplikaadid
            self.af['Timestamp'] = pd.to_datetime(self.af['Ajatempel (UTC)'], unit='s')

            self.af = self.af[self.af['Grupp']=='ee'] # Jätame ainult Eesti andmed
            self.af.loc[:,['Hind']] = self.af['Hind']/10 # €/MWh -> s/kWh
            self.af = self.af.set_index('Timestamp')
            self.af['UTC'] = self.af.index.tz_localize('UTC').tz_convert('Europe/Tallinn').tz_localize(None) # Teisaldame ajatempli ja toome UTC->EET ajavööndi
            self.af = self.af.drop(['Grupp','Ajatempel (UTC)'], axis=1) # Kustutame mittevajalikud veerud
            self.af = self.af.set_index('UTC')
            self.af.columns = ['NordPool hind [s/kWh]']

            # Kirjutame andmed pickle faili
            with open(bd_DATA_DIR + 'af.pickle', 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.HIGHEST_PROTOCOL)
            aeg = datetime.now() - algus
            print(f'files: {aeg.seconds}.{aeg.microseconds}s')

    def __repr__(self):
        tekst = 'Andmeridu:' + str(self.af.shape[0]) + ':'
        for i in range(len(self.af.columns)):
            tekst += '\n'+'{0:02d}. {1}'.format(i, self.af.columns[i])        
        return tekst
    

    def __str__(self):
        algus = self.af.index.min().strftime('%d.%m.%Y %H:%M')
        l6pp = self.af.index.max().strftime('%d.%m.%Y %H:%M')
        tekst = 'NordPool andmed: ' + algus + '-' + l6pp + ' Andmeridu:' + str(self.af.shape[0])
        return tekst
    
    def v(self,veerg=0):
        '''Abifunktsioon veerunimede viitamise lühendamiseks self.af.columns[n] -> v(n)'''
        self.veerg = veerg
        return self.af.columns[veerg]
    
    def tunniandmed(self, **kwargs):
        '''Andmed soovitud perioodiks (start, stopp)'''
        
        self.start = self.af.index.min()
        self.stopp = self.af.index.max()
        
        if kwargs:
            if 'start' in kwargs:
                self.start = kwargs['start']
                
            if 'stopp' in kwargs:
                self.stopp = kwargs['stopp'] + timedelta(days=1) # .replace(minute=0, second=0, microsecond=0)

        # defineerime otsitava vahemiku
        vahemik = (
            (self.af.index >= self.start) &
            (self.af.index < self.stopp)
        )
        andmed = self.af[vahemik]
        
        # grupeerime aasta, kuu, päeva ja tunni kaupa
        levels = [
            andmed.index.year,
            andmed.index.month,
            andmed.index.day,
            andmed.index.hour
        ]
        return andmed.groupby(levels).mean()


class BigData():
    """Suur tabel graafikute tarbeks"""
    def __init__(self, a, i, e, n, y):
        df = pd.concat([a, e, i, n], axis=1)  # Liidame andmed üheks tabeliks
        df["EE üldhind [s/kWh]"] = df.index.to_series().apply(
            y.EEhind)  # Leiame iga tunni elektrienergia hinna üldhinna tabelist
        df["EL üldhind [s/kWh]"] = df.index.to_series().apply(
            y.ELhind)  # Leiame iga tunni võrgutasu hinna üldhinna tabelist
        cols = df.columns # veergude lihtsamaks kasutamiseks
        df['Aquarea kulu [kWh]'] = (df[cols[3]] + df[cols[4]])
        df['Aquarea tulu [kWh]'] = (df[cols[5]] + df[cols[6]])
        df['Aquarea kulu [€]'] = (df[cols[3]] + df[cols[4]]) * (df[cols[10]] + df[cols[11]])/100
        df['Elektri kulu [€]'] = (df[cols[7]]) * (df[cols[10]] + df[cols[11]])/100
        df = df.rename_axis(['Aasta', 'Kuu', 'Päev', 'Tund'])
        self.af = df

    def __repr__(self):
        tekst = 'Andmeridu:' + str(self.af.shape[0]) + ':'
        # Loetleme tulpade nimed
        for i in range(len(self.af.columns)):
            tekst += '\n' + '{0:02d}. {1}'.format(i, self.af.columns[i])
        return tekst

    def __str__(self):
        algus = self.af.index.min()
        l6pp = self.af.index.max()
        tekst = f'Aquarea, Elektrilevi, Ilmateenistuse, NordPooli, EE andmed: {algus}-{l6pp}. Andmeridu: {str(self.af.shape[0])}'
        return tekst

    def tunnikaupa(self):
        """
        Koostab koondtabeli tundide kaupa
        :return:
        +
        02. Actual outdoor temperature [°C]
        07. Elektrienergia kulu [kWh]
        08. Ametlik mõõdetud temperatuur [°C]
        03. Heat mode energy consumption [kW]
        04. Tank mode energy consumption [kW]
        12. Aquarea kulu [kWh]
        13. Aquarea tulu [kWh]
        14. Aquarea kulu [senti]
        15. Elektri kulu [senti]
        -
        00. Zone1: Actual (water outlet/room/pool) temperature [°C]
        01. Actual tank temperature [°C]
        05. Heat mode energy generation [kW]
        06. Tank mode energy generation [kW]
        09. NordPool hind [s/kWh]
        10. EE üldhind [s/kWh]
        11. EL üldhind [s/kWh]
        """
        andmed = self.af[[self.af.columns[i] for i in [8, 2, 3, 4, 7, 13, 12, 15, 14]]]
        return andmed

    def p2evakaupa(self):
        """
        Koostab koondtabeli päevade kaupa
        :return:
        +
        02. Actual outdoor temperature [°C]
        07. Elektrienergia kulu [kWh]
        08. Ametlik mõõdetud temperatuur [°C]
        03. Heat mode energy consumption [kW]
        04. Tank mode energy consumption [kW]
        12. Aquarea kulu [kWh]
        13. Aquarea tulu [kWh]
        14. Aquarea kulu [senti]
        15. Elektri kulu [senti]
        -
        00. Zone1: Actual (water outlet/room/pool) temperature [°C]
        01. Actual tank temperature [°C]
        05. Heat mode energy generation [kW]
        06. Tank mode energy generation [kW]
        09. NordPool hind [s/kWh]
        10. EE üldhind [s/kWh]
        11. EL üldhind [s/kWh]
        """
        andmed_mean = self.af[[self.af.columns[i] for i in [8, 2]]].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             self.af.index.get_level_values('Päev')
             ]
        ).mean()
        andmed_sum = self.af[[self.af.columns[i] for i in [3, 4, 7, 13, 12, 15, 14]]].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             self.af.index.get_level_values('Päev')
             ]
        ).sum()
        andmed = pd.concat([andmed_mean, andmed_sum], axis=1) # Liidame andmed üheks tabeliks
        return andmed

    def kuukaupa(self):
        """
        Koostab koondtabeli kuude kaupa
        :return:
        +
        02. Actual outdoor temperature [°C]
        07. Ametlik mõõdetud temperatuur [°C]
        08. Elektrienergia kulu [kWh]
        03. Heat mode energy consumption [kW]
        04. Tank mode energy consumption [kW]
        12. Aquarea kulu [kWh]
        13. Aquarea tulu [kWh]
        14. Aquarea kulu [senti]
        15. Elektri kulu [senti]
        -
        00. Zone1: Actual (water outlet/room/pool) temperature [°C]
        01. Actual tank temperature [°C]
        05. Heat mode energy generation [kW]
        06. Tank mode energy generation [kW]
        09. NordPool hind [s/kWh]
        10. EE üldhind [s/kWh]
        11. EL üldhind [s/kWh]
        """
        andmed_mean = self.af[[self.af.columns[i] for i in [8, 2]]].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             ]
        ).mean().round(1)
        andmed_sum = self.af[[self.af.columns[i] for i in [3, 4, 7, 13, 12, 15, 14]]].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             ]
        ).sum().round(1)
        andmed = pd.concat([andmed_mean, andmed_sum], axis=1) # Liidame andmed üheks tabeliks
        andmed['COP'] = (andmed[andmed.columns[5]] / andmed[andmed.columns[6]])
        return andmed


    def perioodikaupa(self):
        """
        Koostab koondtabeli perioodi kohta
        :return:
        +
        02. Actual outdoor temperature [°C]
        07. Ametlik mõõdetud temperatuur [°C]
        08. Elektrienergia kulu [kWh]
        12. Aquarea kulu [kWh]
        13. Aquarea tulu [kWh]
        14. Aquarea kulu [senti]
        15. Elektri kulu [senti]
        -
        00. Zone1: Actual (water outlet/room/pool) temperature [°C]
        01. Actual tank temperature [°C]
        03. Heat mode energy consumption [kW]
        04. Tank mode energy consumption [kW]
        05. Heat mode energy generation [kW]
        06. Tank mode energy generation [kW]
        09. NordPool hind [s/kWh]
        10. EE üldhind [s/kWh]
        11. EL üldhind [s/kWh]
        """
        andmed_mean = self.af[[self.af.columns[i] for i in [8, 2]]].mean()
        andmed_sum = self.af[[self.af.columns[i] for i in [7, 13, 12, 15, 14]]].sum()
        andmed = pd.concat([andmed_mean, andmed_sum], axis=0) # Liidame andmed üheks tabeliks
        andmed = pd.DataFrame(andmed, columns=['Periood']).T # teeme andmefreimiks ja transponeerime
        andmed['COP'] = (andmed[andmed.columns[3]] / andmed[andmed.columns[4]])
        return andmed.round(1) # tagastame ümardatud andmed


'''
Aquarea logifaili veerud:
0 Timestamp
1 Operation [1:Off, 2:On]
2 Dry concrete [1:Off, 2:On]
3 Mode [1:Tank only, 2:Heat, 3:Cool, 8:Auto, 9:Auto(Heat), 10:Auto(Cool)]
4 Tank [1:Off, 2:On]
5 Zone1-Zone2 On-Off [1:On-Off, 2:Off-On, 3:On-On]
6 SHP control [1:Disable, 2:Enable]
7 SHP flow control (forbid ΔT) [1:Disable, 2:Enable]
8 Zone1: (water shift/water/room/pool) set temperature for heat mode [°C]
9 Zone1: (water shift/water/room) set temperature for cool mode [°C]
10 Zone2: (water shift/water/room/pool) set temperature for heat mode [°C]
11 Zone2: (water shift/water/room) set temperature for cool  mode [°C]
12 Tank water set temperature [°C]
13 Co-efficient frequency control [%]
14 Current Lv [Lv]
15 External SW [1:Close, 2:Open]
16 Heat-Cool SW [1:Heat, 2:Cool]
17 Powerful (Actual) [1:Off, 2:On]
18 Quiet (Actual) [1:Off, 2:On]
19 3-way valve [1:Room, 2:Tank]
20 Defrost (Actual) [1:Off, 2:On]
21 Room heater (Actual) [1:Off, 2:On]
22 Tank heater (Actual) [1:Off, 2:On]
23 Solar (Actual) [1:Off, 2:On]
24 Bivalent (Actual) [1:Off, 2:On]
25 Current error status [0:No error pop up screen in RC LCD, 1:Error pop up screen in RC LCD]
26 Backup heater 1 status (Actual) [1:Off, 2:On]
27 Backup heater 2 status (Actual) [1:Off, 2:On]
28 Backup heater 3 status (Actual) [1:Off, 2:On]
29 2 Zone pump 1 status (Actual) [1:Off, 2:On]
30 2 Zone pump 2 status (Actual) [1:Off, 2:On]
31 Sterilization status (Actual) [1:Off, 2:On]
32 Zone1: Actual (water outlet/room/pool) temperature [°C]
33 Zone2: Actual (water outlet/room/pool) temperature [°C]
34 Actual tank temperature [°C]
35 Actual outdoor temperature [°C]
36 Inlet water temperature [°C]
37 Outlet water temperature [°C]
38 Zone1: Water temperature [°C]
39 Zone2: Water temperature [°C]
40 Zone1: Water temperature (Target) [°C]
41 Zone2: Water temperature (Target) [°C]
42 Buffer tank: Water temperature [°C]
43 Solar: Water temperature [°C]
44 Pool: Water temperature [°C]
45 Outlet water temperature (Target) [°C]
46 Outlet 2 temperature [°C]
47 Discharge temperature [°C]
48 Room thermostat internal sensor temperature [°C]
49 Indoor piping temperature [°C]
50 Outdoor piping temperature [°C]
51 Defrost temperature [°C]
52 EVA outlet temperature [°C]
53 Bypass outlet temperature [°C]
54 IPM temperature [°C]
55 High pressure [kgf/cm2]
56 Low pressure [kgf/cm2]
57 Outdoor current [A]
58 Compressor frequency [Hz]
59 Pump flow rate [L/min]
60 Pump speed [r/min]
61 Pump duty [duty]
62 Fan motor speed 1 [r/min]
63 Fan motor speed 2 [r/min]
64 2 Zone mixing valve 1 opening [sec]
65 2 Zone mixing valve 2 opening [sec]
66 Heat mode energy consumption [kW]
67 Heat mode energy generation [kW]
68 Cool mode energy consumption [kW]
69 Cool mode energy generation [kW]
70 Tank mode energy consumption [kW]
71 Tank mode energy generation [kW]
'''

# Valitud andmete veerud:
'''
00. Operation [1:Off, 2:On]
01. Mode [1:Tank only, 2:Heat, 3:Cool, 8:Auto, 9:Auto(Heat), 10:Auto(Cool)]
02. Zone1: (water shift/water/room/pool) set temperature for heat mode [°C]
03. Zone1: (water shift/water/room) set temperature for cool mode [°C]
04. Tank water set temperature [°C]
05. Co-efficient frequency control [%]
06. Powerful (Actual) [1:Off, 2:On]
07. 3-way valve [1:Room, 2:Tank]
08. Defrost (Actual) [1:Off, 2:On]
09. Room heater (Actual) [1:Off, 2:On]
10. Tank heater (Actual) [1:Off, 2:On]
11. Current error status [0:No error pop up screen in RC LCD, 1:Error pop up screen in RC LCD]
12. Zone1: Actual (water outlet/room/pool) temperature [°C]
13. Actual tank temperature [°C]
14. Actual outdoor temperature [°C]
15. Inlet water temperature [°C]
16. Outlet water temperature [°C]
17. Zone1: Water temperature [°C]
18. Zone1: Water temperature (Target) [°C]
19. Buffer tank: Water temperature [°C]
20. Outlet water temperature (Target) [°C]
21. Discharge temperature [°C]
22. Indoor piping temperature [°C]
23. Outdoor piping temperature [°C]
24. Defrost temperature [°C]
25. Outdoor current [A]
26. Compressor frequency [Hz]
27. Pump flow rate [L/min]
28. Heat mode energy consumption [kW]
29. Heat mode energy generation [kW]
30. Tank mode energy consumption [kW]
31. Tank mode energy generation [kW]
32. Timestamp
'''

if __name__ == "__main__":

    DATA_DIR = 'static/ajalugu/data/'
    
    print('Arvutame...')
    bdy = EEYldHindData()
    print(bdy)
    bda = AquareaData()
    print(bda)
    bde = ElektrileviData()
    print(bde)
    bdi = IlmateenistusData()
    print(bdi)
    bdn = NordPoolData()
    print(bdn)

    # Koondame ühte tabelisse
    bd = BigData(
        bda.tunniandmed(),
        bde.tunniandmed(),
        bdi.tunniandmed(),
        bdn.tunniandmed(),
        bdy
    )
    print(bd)

