from datetime import date, datetime, timedelta
import os
import pickle

import numpy as np
import pandas as pd
import pytz

from django.conf import settings

try:
    DATA_DIR = os.path.join(settings.STATIC_ROOT, 'data')
except:
    from pathlib import Path
    DATA_DIR = Path(__file__).resolve().parent.parent / 'static' / 'data'
print(DATA_DIR)

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def nulliga(number):
    return str("{0:02d}").format(number)

def soodus(aeg):
    tz = pytz.timezone('Europe/Tallinn')
    aeg = aeg.replace(tzinfo=tz)
    aasta = aeg.year
    if aeg.weekday() > 4: # 5-laupäev, 6-pühapäev
        return True
    if aeg >= datetime(2022, 3, 1, tzinfo=tz): # alates 01.03.2022 uus soodusaja arvestus
        riigipyhad = [
            (aasta, 1, 1),
            (aasta, 2, 24),
            (2022, 4, 15), (2023, 4, 7), (2024, 3, 29), (2025, 4, 18), # Suur reede
            (2022, 4, 17), (2023, 4, 9), (2024, 3, 31), # Ülestõusmispühade 1. püha P
            (aasta, 5, 1),
            (2022, 6, 5), (2023, 5, 28), (2024, 5, 19), # Nelipühade 1. püha P
            (aasta, 6, 23),
            (aasta, 6, 24),
            (aasta, 8, 20),
            (aasta, 12, 24),
            (aasta, 12, 25),
            (aasta, 12, 26),
        ]
        if aeg.date() in [date(*datetuple) for datetuple in riigipyhad]:
            return True
        if aeg.hour < 7 or aeg.hour >= 22:
            return True
    else:
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
        bd_DATA_DIR = os.path.join(DATA_DIR, 'bdy')
        ajf = []
        with os.scandir(bd_DATA_DIR) as it:
            for entry in it:
                if entry.name.startswith('EE_yldhind') and entry.is_file():
                    fail = os.path.join(bd_DATA_DIR, entry.name)
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
        tekst = f'EE hinnaajaloo andmed: {algus_aasta}-{algus_kuu} - {l6pp_aasta}-{l6pp_kuu} Andmeridu: {self.af.shape[0]}'
        for i in range(len(self.af.columns)):
            tekst += '\n' + '{0:02d}. {1}'.format(i, self.af.columns[i])
        return tekst
    
    def v(self,veerg=0):
        '''Veerunimede viitamise lühendamiseks self.af.columns[n] -> v(n)'''
        self.veerg = veerg
        return self.af.columns[veerg]

    # tagastab EE elektrienergia hinna km-ga
    def EEhind(self, aeg):
        aeg = datetime(*aeg)
        aastakuu = "{0:04d}{1:02d}".format(aeg.year, aeg.month)
        if aastakuu in self.af.index:
            if soodus(aeg):
                return self.af['EE_Soodus [s/kWh]'][aastakuu]
            else:
                return self.af['EE_Normaal [s/kWh]'][aastakuu]
        else:
            return 0 # perioodi EE üldhind ei ole teada

    # tagastab EL elektrienergia edastamise hinna km-ga
    def ELhind(self, aeg):
        aeg = datetime(*aeg)
        aastakuu = "{0:04d}{1:02d}".format(aeg.year, aeg.month)
        if aastakuu in self.af.index:
            if soodus(aeg):
                return self.af['EL_Soodus [s/kWh]'][aastakuu]
            else:
                return self.af['EL_Normaal [s/kWh]'][aastakuu]
        else:
            return 0 # perioodi EL üldhind ei ole teada

    # tagastab EE bärsihinnale lisatava marginaali km+ga
    def EEborsimarginaal(self, aeg):
        aeg = datetime(*aeg)
        if aeg < datetime(2023, 6, 1):
            return 0.55
        else:
            return 0.44

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
        bd_DATA_DIR = os.path.join(DATA_DIR, 'bda')
        pickle_file_name = os.path.join(bd_DATA_DIR, 'af.pickle')
        algus = datetime.now()
        if os.path.isfile(pickle_file_name):
            src = 'pickle'
            with open(pickle_file_name, 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
        else:
            src = 'files'
            ajf = []

            cols = [
                'Timestamp',
                'Operation [1:Off, 2:On]',
                'Inlet water temperature [°C]',
                'Outlet water temperature [°C]',
                'Zone1: Actual (water outlet/room/pool) temperature [°C]',
                'Zone1: Water temperature (Target) [°C]',
                'Zone2: Actual (water outlet/room/pool) temperature [°C]',
                'Zone2: Water temperature (Target) [°C]',
                'Actual tank temperature [°C]',
                'Tank water set temperature [°C]',
                'Actual outdoor temperature [°C]',
                'Heat mode energy consumption [kW]',
                'Tank mode energy consumption [kW]',
                'Heat mode energy generation [kW]',
                'Tank mode energy generation [kW]',
            ]

            dtype = {
                # 'Timestamp',
                'Operation [1:Off, 2:On]': np.uint8,
                'Dry concrete [1:Off, 2:On]': np.uint8,
                'Mode [1:Tank only, 2:Heat, 3:Cool, 8:Auto, 9:Auto(Heat), 10:Auto(Cool)]': np.int8,
                'Tank [1:Off, 2:On]': np.uint8,
                'Zone1-Zone2 On-Off [1:On-Off, 2:Off-On, 3:On-On]': np.uint8,
                'SHP control [1:Disable, 2:Enable]': np.uint8,
                'SHP flow control (forbid ΔT) [1:Disable, 2:Enable]': np.uint8,
                'Zone1: (water shift/water/room/pool) set temperature for heat mode [°C]': np.float16,
                'Zone1: (water shift/water/room) set temperature for cool mode [°C]': np.float16,
                'Zone2: (water shift/water/room/pool) set temperature for heat mode [°C]': np.float16,
                'Zone2: (water shift/water/room) set temperature for cool  mode [°C]': np.float16,
                'Tank water set temperature [°C]': np.uint8,
                'Co-efficient frequency control [%]': np.float16,
                'Current Lv [Lv]': np.float16,
                'External SW [1:Close, 2:Open]': np.uint8,
                'Heat-Cool SW [1:Heat, 2:Cool]': np.uint8,
                'Powerful (Actual) [1:Off, 2:On]': np.uint8,
                'Quiet (Actual) [1:Off, 2:On]': np.uint8,
                '3-way valve [1:Room, 2:Tank]': np.uint8,
                'Defrost (Actual) [1:Off, 2:On]': np.uint8,
                'Room heater (Actual) [1:Off, 2:On]': np.uint8,
                'Tank heater (Actual) [1:Off, 2:On]': np.uint8,
                'Solar (Actual) [1:Off, 2:On]': np.uint8,
                'Bivalent (Actual) [1:Off, 2:On]': np.uint8,
                'Current error status [0:No error pop up screen in RC LCD, 1:Error pop up screen in RC LCD]': np.uint8,
                'Backup heater 1 status (Actual) [1:Off, 2:On]': np.uint8,
                'Backup heater 2 status (Actual) [1:Off, 2:On]': np.uint8,
                'Backup heater 3 status (Actual) [1:Off, 2:On]': np.uint8,
                '2 Zone pump 1 status (Actual) [1:Off, 2:On]': np.uint8,
                '2 Zone pump 2 status (Actual) [1:Off, 2:On]': np.uint8,
                'Sterilization status (Actual) [1:Off, 2:On]': np.uint8,
                'Zone1: Actual (water outlet/room/pool) temperature [°C]': np.float16,
                'Zone2: Actual (water outlet/room/pool) temperature [°C]': np.float16,
                'Actual tank temperature [°C]': np.float16,
                'Actual outdoor temperature [°C]': np.float16,
                'Inlet water temperature [°C]': np.float16,
                'Outlet water temperature [°C]': np.float16,
                'Zone1: Water temperature [°C]': np.float16,
                'Zone2: Water temperature [°C]': np.float16,
                'Zone1: Water temperature (Target) [°C]': np.float16,
                'Zone2: Water temperature (Target) [°C]': np.float16,
                'Buffer tank: Water temperature [°C]': np.float16,
                'Solar: Water temperature [°C]': np.float16,
                'Pool: Water temperature [°C]': np.float16,
                'Outlet water temperature (Target) [°C]': np.float16,
                'Outlet 2 temperature [°C]': np.float16,
                'Discharge temperature [°C]': np.float16,
                'Room thermostat internal sensor temperature [°C]': np.float16,
                'Indoor piping temperature [°C]': np.float16,
                'Outdoor piping temperature [°C]': np.float16,
                'Defrost temperature [°C]': np.float16,
                'EVA outlet temperature [°C]': np.float16,
                'Bypass outlet temperature [°C]': np.float16,
                'IPM temperature [°C]': np.float16,
                'High pressure [kgf/cm2]': np.float16,
                'Low pressure [kgf/cm2]': np.float16,
                'Outdoor current [A]': np.float16,
                'Compressor frequency [Hz]': np.int16,
                'Pump flow rate [L/min]': np.float16,
                'Pump speed [r/min]': np.int16,
                'Pump duty [duty]': np.float16,
                'Fan motor speed 1 [r/min]': np.int16,
                'Fan motor speed 2 [r/min]': np.int16,
                '2 Zone mixing valve 1 opening [sec]': np.int16,
                '2 Zone mixing valve 2 opening [sec]': np.int16,
                'Heat mode energy consumption [kW]': np.float16,
                'Heat mode energy generation [kW]': np.float16,
                'Cool mode energy consumption [kW]': np.float16,
                'Cool mode energy generation [kW]': np.float16,
                'Tank mode energy consumption [kW]': np.float16,
                'Tank mode energy generation [kW]': np.float16,
                'RC-2: Room thermostat internal sensor temperature [°C]': np.float16
            }

            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    # print(entry)
                    # 25.03.2024 muudeti failiformaati
                    if entry.name.startswith('Statistics_B197792584') and entry.is_file(): # Loeme ainult Aquarea logifailid andmefreimidesse
                        fail = os.path.join(bd_DATA_DIR, entry.name)
                        print('Loeme faili: ', fail)
                        df = pd.read_csv(
                            fail,
                            delimiter=',',
                            decimal='.',
                            dtype=dtype,
                            parse_dates=[0],
                            usecols=cols,
                        )
                        # print(df.memory_usage(index=True, deep=False))
                        # break
                        df = df.set_index('Timestamp')
                        ajf.append(df)

            print('Liidame andmed ja kõrvaldame duplikaadid...')
            for n in range(len(ajf)):
                if n == 0:
                    self.af = ajf[n]
                else:
                    self.af = pd.concat([self.af, ajf[n]], axis=0)
            # self.af = self.af.drop_duplicates()  # Ühendame andmefreimid ja kõrvaldame duplikaadid
            self.af = self.af[self.af.index.duplicated(keep='first')==False]  # Ühendame andmefreimid ja kõrvaldame duplikaadid
            # self.af = self.af.set_index('Timestamp')

            # Kirjutame andmed pickle faili
            with open(pickle_file_name, 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.DEFAULT_PROTOCOL)

        aeg = datetime.now() - algus
        print(f'{src}: {aeg.seconds}.{aeg.microseconds:06d}s')

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

        cols = [
            'Zone1: Actual (water outlet/room/pool) temperature [°C]',
            'Zone2: Actual (water outlet/room/pool) temperature [°C]',
            'Actual tank temperature [°C]',
            'Actual outdoor temperature [°C]',
            'Heat mode energy consumption [kW]',
            'Tank mode energy consumption [kW]',
            'Heat mode energy generation [kW]',
            'Tank mode energy generation [kW]'
        ]

        data = andmed[cols]
        data = data.groupby(levels).mean()

        return data


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
        df = self.tunniandmed(start=self.start, stopp=self.stopp)
        # Anname tulpadele lühemad pealkirjad
        df.columns = ['temp_heat_zone1', 'temp_heat_zone2', 'temp_tank', 'temp_out', 'con_heat', 'con_tank', 'gen_heat', 'gen_tank']
        # sel_cols = ['con_heat', 'con_tank', 'gen_heat', 'gen_tank']
        # Perioodi andmed kokku
        # df_period = df[sel_cols].sum()
        # cop_period = df_period['gen_heat'] / df_period['con_heat']
        # Perioodi andmed kuude kaupa
        # df_months = df[sel_cols].groupby([df.index.year, df.index.month]).sum()
        # cop_months = df_months['gen_heat'] / df_months['con_heat']
        # Perioodi andmed päevade kaupa
        # df_days = df[sel_cols].groupby([df.index.year, df.index.month, df.index.day]).sum()
        # cop_days = df_days['gen_heat'] / df_days['con_heat']
        # Perioodi andmed tundide kaupa
        df['cop'] = df['gen_heat'] / df['con_heat']
        # Loome sõnastiku
        andmed = {
            # 'period': cop_period,
            # 'months': cop_months,
            # 'days': cop_days,
            'hours': df
        }
        return andmed


class ElektrileviData():
    '''Andmed Elektrilevi andmebaasist ja nende töötlused'''   
    
    def __init__(self):
        print('Elektrilevi ', end='')
        bd_DATA_DIR = os.path.join(DATA_DIR, 'bde')
        pickle_file_name = os.path.join(bd_DATA_DIR, 'af.pickle')
        algus = datetime.now()
        if os.path.isfile(pickle_file_name):
            with open(pickle_file_name, 'rb') as f:
                src = 'pickle'
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
        else:
            src = 'files'
            ajf = []
            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    if entry.name.startswith(
                            'Elektrilevi_S9a') and entry.is_file():  # Loeme ainult Elektrilevi logifailid andmefreimidesse
                        fail = os.path.join(bd_DATA_DIR, entry.name)
                        skiprows = 6
                        decimal = ','
                        # 2021.03 muudeti failiformaati
                        # 2022.02 muudeti failiformaati
                        # 2025.04 muudeti failiformaati
                        faili_moodustamise_aeg = fail.split('.')[0][-6:]
                        faili_moodustamise_aeg_aasta = int(faili_moodustamise_aeg[:4])
                        faili_moodustamise_aeg_kuu = int(faili_moodustamise_aeg[-2:])
                        usecols = [0,2]
                        if datetime(faili_moodustamise_aeg_aasta, faili_moodustamise_aeg_kuu, 1) > datetime(2021, 2, 28):
                            skiprows = 4
                        if datetime(faili_moodustamise_aeg_aasta, faili_moodustamise_aeg_kuu, 1) > datetime(2022, 1, 31):
                            skiprows = 12
                            usecols = [0, 4]
                        if datetime(faili_moodustamise_aeg_aasta, faili_moodustamise_aeg_kuu, 1) > datetime(2025, 2, 28):
                            skiprows = 12
                            usecols = [0, 2]
                        print('Loeme faili: ', fail)
                        data = pd.read_csv(
                            fail,
                            delimiter=';',
                            skiprows=skiprows,
                            header=None, names = ['Timestamp','Elektrienergia kulu [kWh]'], # Jätame ära algusread ja nimetame ise veerud
                            parse_dates=[0], dayfirst = True, # Konverteerime 1. veeru Euroopa kuupäevatüüpi
                            decimal = decimal, # Murdosa eraldajaks on koma
                            usecols=usecols
                        ).dropna(how='any') # Loeme ainult täielike andmetega veerud Algusaeg, Lõppaeg ja Kogus
                        # alates 2025.10 15-minuti kaupa arvestus
                        if datetime(faili_moodustamise_aeg_aasta, faili_moodustamise_aeg_kuu, 1) > datetime(2025, 2, 28):
                            data = data.set_index('Timestamp')
                            data = data.resample('H').sum()
                            data = data.rename_axis('Timestamp').reset_index()
                        ajf.append(data)
            self.af = pd.concat(ajf[:], axis=0).drop_duplicates() # Ühendame andmefreimid ja kõrvaldame duplikaadid
            self.af = self.af.set_index('Timestamp')

            # Kirjutame andmed pickle faili
            with open(pickle_file_name, 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.DEFAULT_PROTOCOL)
        aeg = datetime.now() - algus
        print(f'{src}: {aeg.seconds}.{aeg.microseconds:06d}s')

    def __repr__(self):
        tekst = 'Andmeridu:' + str(self.af.shape[0]) + ':'
        for i in range(len(self.af.columns)):
            tekst += '\n'+'{0:02d}. {1}'.format(i, self.af.columns[i])        
        return tekst

    def __str__(self):
        algus = self.af.index.min().strftime('%d.%m.%Y %H:%M')
        l6pp = self.af.index.max().strftime('%d.%m.%Y %H:%M')
        tekst = 'Elektrilevi andmed: ' + algus + '-' + l6pp + ' Andmeridu:' + str(self.af.shape[0])
        for i in range(len(self.af.columns)):
            tekst += '\n' + '{0:02d}. {1}'.format(i, self.af.columns[i])
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
        df_filtered = self.af[vahemik]
        # grupeerime aasta, kuu, päeva ja tunni kaupa
        levels = [
            df_filtered.index.year,
            df_filtered.index.month,
            df_filtered.index.day,
            df_filtered.index.hour
        ]
        return df_filtered.groupby(levels).mean()

    def n2dalaandmed(self, **kwargs):
        '''Andmed soovitud perioodiks (start, stopp)'''
        self.start = self.af.index.min()
        self.stopp = self.af.index.max()

        if kwargs:
            if 'start' in kwargs:
                self.start = kwargs['start']

            if 'stopp' in kwargs:
                self.stopp = kwargs['stopp'] + timedelta(days=1)  # .replace(minute=0, second=0, microsecond=0)

        # defineerime otsitava vahemiku
        vahemik = (
                (self.af.index >= self.start) &
                (self.af.index < self.stopp)
        )
        df_filtered = self.af[vahemik]

        # grupeerime aasta, kuu, päeva ja tunni kaupa
        levels = [
            df_filtered.index.weekday,
            df_filtered.index.hour
        ]
        return {
            'andmed': df_filtered.groupby(levels).mean(),
            'count': df_filtered.shape[0],
            'value_max': self.af[vahemik].max()['Elektrienergia kulu [kWh]']
        }
        

class IlmateenistusData():
    '''Andmed Ilmateenistusest ja nende töötlused'''
    
    def __init__(self):
        print('Ilmateenistus ', end='')
        bd_DATA_DIR = os.path.join(DATA_DIR, 'bdi')
        pickle_file_name = os.path.join(bd_DATA_DIR, 'af.pickle')
        algus = datetime.now()
        if os.path.isfile(pickle_file_name):
            src = 'pickle'
            with open(pickle_file_name, 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
        else:
            src = 'files'
            ajf = []
            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    if entry.name.startswith(
                            'Ilmateenistus_Valga') and entry.is_file():  # Loeme ainult Elektrilevi logifailid andmefreimidesse
                        fail = os.path.join(bd_DATA_DIR, entry.name)
                        date_format = '%Y-%m-%d %H:%M:%S'
                        # date_parser = lambda t: datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
                        
                        # 2022.06 muudeti kuupäevaformaati
                        faili_moodustamise_aeg = fail.split('.')[0][-6:]
                        faili_moodustamise_aeg_aasta = int(faili_moodustamise_aeg[:4])
                        faili_moodustamise_aeg_kuu = int(faili_moodustamise_aeg[-2:])
                        if datetime(faili_moodustamise_aeg_aasta, faili_moodustamise_aeg_kuu, 1) > datetime(2022, 5, 31):
                            # date_parser = lambda t: datetime.strptime(t, '%Y-%m-%d %H:%M:%S:00')
                            date_format = '%Y-%m-%d %H:%M:%S:00'
                        print('Loeme faili: ', fail)
                        ajf.append(
                            pd.read_csv(
                                fail, delimiter=',',
                                skiprows=1, header=None, decimal = '.',
                                usecols=[1,2,3,6,11,13],
                                names = [
                                    'Ametlik mõõdetud temperatuur [°C]',
                                    'Niiskus',
                                    'Õhurõhk',
                                    'Tuul',
                                    'Sademed',
                                    'Timestamp'
                                ], # Kasutame osa veerge ja paneme nimed
                                parse_dates=[5],
                                date_format=date_format,
                                # date_parser=date_parser
                            )
                        )
            self.af = pd.concat(ajf[:], axis=0).drop_duplicates() # Ühendame andmefreimid ja kõrvaldame duplikaadid
            self.af = self.af.set_index('Timestamp')

            # Kirjutame andmed pickle faili
            with open(pickle_file_name, 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.DEFAULT_PROTOCOL)
        aeg = datetime.now() - algus
        print(f'{src}: {aeg.seconds}.{aeg.microseconds:06d}s')

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
        bd_DATA_DIR = os.path.join(DATA_DIR, 'bdn')
        pickle_file_name = os.path.join(bd_DATA_DIR, 'af.pickle')
        algus = datetime.now()
        if os.path.isfile(pickle_file_name):
            src = 'pickle'
            with open(pickle_file_name, 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.af = pickle.load(f)
        else:
            src = 'files'
            ajf = []
            with os.scandir(bd_DATA_DIR) as it:
                for entry in it:
                    if entry.name.startswith(
                            'nps-export') and entry.is_file():  # Loeme ainult Elektrilevi logifailid andmefreimidesse
                        fail = os.path.join(bd_DATA_DIR, entry.name)
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
            with open(pickle_file_name, 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(self.af, f, pickle.DEFAULT_PROTOCOL)
        aeg = datetime.now() - algus
        print(f'{src}: {aeg.seconds}.{aeg.microseconds:06d}s')

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

    def n2dalaandmed(self, **kwargs):
        '''Andmed soovitud perioodiks (start, stopp)'''

        self.start = self.af.index.min()
        self.stopp = self.af.index.max()

        if kwargs:
            if 'start' in kwargs:
                self.start = kwargs['start']

            if 'stopp' in kwargs:
                self.stopp = kwargs['stopp'] + timedelta(days=1)  # .replace(minute=0, second=0, microsecond=0)

        # defineerime otsitava vahemiku
        vahemik = (
                (self.af.index >= self.start) &
                (self.af.index < self.stopp)
        )
        df_filtered = self.af[vahemik]

        # grupeerime aasta, kuu, päeva ja tunni kaupa
        levels = [
            df_filtered.index.weekday,
            df_filtered.index.hour
        ]
        return {
            'andmed': df_filtered.groupby(levels).mean(),
            'count': df_filtered.shape[0],
            'value_max': self.af[vahemik].max()['NordPool hind [s/kWh]']
        }


class BigData():
    """Suur tabel graafikute tarbeks"""
    def __init__(self, a, i, e, n, y):
        df = pd.concat([a, e, i, n], axis=1)  # Liidame andmed üheks tabeliks
        df["EE lepingu hind [s/kWh]"] = df.index.to_series().apply(
            y.EEhind)  # Leiame iga tunni elektrienergia hinna üldhinna tabelist
        df["EL lepingu hind [s/kWh]"] = df.index.to_series().apply(
            y.ELhind)  # Leiame iga tunni võrgutasu hinna üldhinna tabelist
        df["EE börsi marginaal [s/kWh]"] = df.index.to_series().apply(
            y.EEborsimarginaal)  # Leiame iga tunni marginaali
        cols = df.columns # veergude lihtsamaks kasutamiseks

        # MARGINAAL = 0.55

        df['Aquarea kulu [kWh]'] = (
                df['Heat mode energy consumption [kW]'] +
                df['Tank mode energy consumption [kW]']
        )
        df['Aquarea tulu [kWh]'] = (
                df['Heat mode energy generation [kW]'] +
                df['Tank mode energy generation [kW]']
        )
        df['Aquarea kulu [€]'] = (
            df['Heat mode energy consumption [kW]'] +
            df['Tank mode energy consumption [kW]']
        ) * (
            df['EE lepingu hind [s/kWh]'] +
            df['EL lepingu hind [s/kWh]']
        ) / 100
        df['Elektri kulu EE+EL [€]'] = (
            df['Elektrienergia kulu [kWh]']
        ) * (
            df['EE lepingu hind [s/kWh]'] +
            df['EL lepingu hind [s/kWh]']
        ) / 100

        df['EE leping [€]'] = df['Elektrienergia kulu [kWh]'] * df['EE lepingu hind [s/kWh]'] / 100
        # df['EE üldteenus [€]'] = df[cols[8]] * df[cols[11]] / 100
        df['EE muutuv [€]'] = df['Elektrienergia kulu [kWh]'] * (
                df['NordPool hind [s/kWh]'] + df["EE börsi marginaal [s/kWh]"]
        ) / 100

        df = df.rename_axis(['Aasta', 'Kuu', 'Päev', 'Tund'])

        df['Soodusaeg'] = df.apply(lambda row: soodus(datetime(*row.name)), axis = 1)

        print('Aquarea.Bigdata:')
        cols = df.columns  # veergude lihtsamaks kasutamiseks
        for col in range(len(cols)):
            print(col, cols[col])

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
        for i in range(len(self.af.columns)):
            tekst += '\n' + '{0:02d}. {1}'.format(i, self.af.columns[i])
        return tekst

    def tunnikaupa(self, verbose=False):
        """
        Koostab koondtabeli tundide kaupa
        :return:
        """
        cols = [
            'Ametlik mõõdetud temperatuur [°C]',
            'Actual outdoor temperature [°C]',
            'Heat mode energy consumption [kW]',
            'Tank mode energy consumption [kW]',
            'Heat mode energy generation [kW]',
            'Tank mode energy generation [kW]',
            'Elektrienergia kulu [kWh]',
            'Aquarea kulu [kWh]',
            'Aquarea tulu [kWh]',
            'Aquarea kulu [€]',
            'Elektri kulu EE+EL [€]',
            'NordPool hind [s/kWh]',
            'EE leping [€]',
            'EE muutuv [€]',
            'Soodusaeg'
        ]
        andmed = self.af[cols]

        if verbose:
            print('Aquarea.tunnikaupa:')
            cols = andmed.columns
            for col in range(len(cols)):
                print(col, cols[col])

        return andmed

    def p2evakaupa(self, verbose=False):
        """
        Koostab koondtabeli päevade kaupa
        :return:
        TODO: v2ljund
        """

        cols = [
            'Ametlik mõõdetud temperatuur [°C]',
            'Actual outdoor temperature [°C]',
            'Zone1: Actual (water outlet/room/pool) temperature [°C]',
            'Zone2: Actual (water outlet/room/pool) temperature [°C]'
        ]
        andmed_mean = self.af[cols].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             self.af.index.get_level_values('Päev')
             ]
        ).mean()
        cols = [
            'Heat mode energy consumption [kW]',
            'Tank mode energy consumption [kW]',
            'Heat mode energy generation [kW]',
            'Tank mode energy generation [kW]',
            'Elektrienergia kulu [kWh]',
            'Aquarea kulu [kWh]',
            'Aquarea tulu [kWh]',
            'Aquarea kulu [€]',
            'Elektri kulu EE+EL [€]',
            'EE leping [€]',
            'EE muutuv [€]'
        ]
        andmed_sum = self.af[cols].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             self.af.index.get_level_values('Päev')
             ]
        ).sum()
        andmed = pd.concat([andmed_mean, andmed_sum], axis=1) # Liidame andmed üheks tabeliks

        # arvutame kasuteguri
        andmed['COP'] = (
                (andmed['Heat mode energy generation [kW]'] + andmed['Tank mode energy generation [kW]']) /
                (andmed['Heat mode energy consumption [kW]'] + andmed['Tank mode energy consumption [kW]'])
        ).round(1)

        andmed['COP_heat'] = (
                andmed['Heat mode energy generation [kW]'] / andmed['Heat mode energy consumption [kW]']
        ).round(1)
        andmed['COP_tank'] = (
                andmed['Tank mode energy generation [kW]'] / andmed['Tank mode energy consumption [kW]']
        ).round(1)

        if verbose:
            print('Aquarea.p2evakaupa:')
            cols = andmed.columns
            for col in range(len(cols)):
                print(col, cols[col])

        return andmed

    def kuukaupa(self, verbose=False):
        """
        Koostab koondtabeli kuude kaupa
        :return:
        TODO: v2ljund
        """
        cols = [
            'Ametlik mõõdetud temperatuur [°C]',
            'Actual outdoor temperature [°C]',
            'Zone1: Actual (water outlet/room/pool) temperature [°C]',
            'Zone2: Actual (water outlet/room/pool) temperature [°C]'
        ]
        andmed_mean = self.af[cols].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             ]
        ).mean().round(2)
        cols = [
            'Heat mode energy consumption [kW]',
            'Tank mode energy consumption [kW]',
            'Heat mode energy generation [kW]',
            'Tank mode energy generation [kW]',
            'Elektrienergia kulu [kWh]',
            'Aquarea kulu [kWh]',
            'Aquarea tulu [kWh]',
            'Aquarea kulu [€]',
            'Elektri kulu EE+EL [€]',
            'EE leping [€]',
            'EE muutuv [€]'
        ]
        andmed_sum = self.af[cols].groupby(
            [self.af.index.get_level_values('Aasta'),
             self.af.index.get_level_values('Kuu'),
             ]
        ).sum().round(1)
        andmed = pd.concat([andmed_mean, andmed_sum], axis=1) # Liidame andmed üheks tabeliks

        # arvutame kasuteguri
        andmed['COP'] = (
                (andmed['Heat mode energy generation [kW]'] + andmed['Tank mode energy generation [kW]']) /
                (andmed['Heat mode energy consumption [kW]'] + andmed['Tank mode energy consumption [kW]'])
        ).round(1)

        andmed['COP_heat'] = (
                andmed['Heat mode energy generation [kW]'] / andmed['Heat mode energy consumption [kW]']
        ).round(1)
        andmed['COP_tank'] = (
                andmed['Tank mode energy generation [kW]'] / andmed['Tank mode energy consumption [kW]']
        ).round(1)

        if verbose:
            print('Aquarea.kuukaupa:')
            cols = andmed.columns
            for col in range(len(cols)):
                print(col, cols[col])

        return andmed

    def perioodikaupa(self):
        """
        Koostab koondtabeli perioodi kohta
        :return:
        TODO: v2ljund
        """
        cols = [
            'Ametlik mõõdetud temperatuur [°C]',
            'Actual tank temperature [°C]'
        ]
        andmed_mean = self.af[cols].mean()

        cols = [
            'Elektrienergia kulu [kWh]',
            'Aquarea kulu [kWh]',
            'Aquarea tulu [kWh]',
            'Aquarea kulu [€]',
            'Elektri kulu EE+EL [€]'
        ]
        andmed_sum = self.af[cols].sum()
        andmed = pd.concat([andmed_mean, andmed_sum], axis=0) # Liidame andmed üheks tabeliks
        andmed = pd.DataFrame(andmed, columns=['Periood']).T # teeme andmefreimiks ja transponeerime
        andmed['COP'] = (andmed['Aquarea tulu [kWh]'] / andmed['Aquarea kulu [kWh]'])
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
    from pathlib import Path
    DATA_DIR = Path(__file__).resolve().parent.parent / 'static' / 'data'
    # DATA_DIR = 'static/ajalugu/data/'
    
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

    result = bd.tunnikaupa()
    # result = bd.kuukaupa(verbose=True)
    # result.to_csv('tunnikaupa.csv')

    # print(result['Actual outdoor temperature [°C]'].mean())
    # result['Actual outdoor temperature [°C]'].hist()
    import matplotlib.pyplot as plt

    # plot
    # plt.title('temps')
    # plt.show()

    # Kytteperioodi tunnid
    mask = (
        ((result.index.get_level_values(1) > 9) | (result.index.get_level_values(1) < 5)) |
        (
            ((result.index.get_level_values(1) == 5) & (result.index.get_level_values(2) < 16)) |
            ((result.index.get_level_values(1) == 9) & (result.index.get_level_values(2) > 14))
        )
    )
    print('Kokku tunniandmete ridu', result.shape[0], 'sh soodusajaga', result.loc[mask].shape[0])

    # Testandmed
    # df = bd.p2evakaupa()
    # df = bd.kuukaupa()
    # df = bd.perioodikaupa()
    df = bd.tunnikaupa()
    mask = (df.index.get_level_values(0) > 2024)
    dff = df.loc[mask]
    cols = [
        'Elektri kulu EE+EL [€]', 
        'EE leping [€]', 
        'EE muutuv [€]'
    ]
    result = dff[cols].groupby([dff.index.get_level_values('Kuu'), dff.index.get_level_values('Päev')]).sum()
    # print(result)

    # V6rdlus lepingu hind vs börsihind
    cols = [
        'Elektrienergia kulu [kWh]', 
        'EE leping [€]', 
        'EE muutuv [€]'
    ]
    col_elektrienergia_kulu_sum = dff[cols].\
        groupby([dff.index.get_level_values('Aasta'), dff.index.get_level_values('Kuu'), dff.index.get_level_values('Päev')]).\
        sum().round(2)
    cols = ['NordPool hind [s/kWh]']
    col_nordpool_hind_min = dff[cols]. \
        groupby([dff.index.get_level_values('Aasta'), dff.index.get_level_values('Kuu'), dff.index.get_level_values('Päev')]). \
        min().round(2)
    result = pd.concat(
        [col_elektrienergia_kulu_sum, col_nordpool_hind_min],
        axis=1
    )  # Liidame andmed üheks tabeliks
    # print(result.columns)

    MARGINAAL = 0.44 / 1.2 # EE marginaal km-ta
    # Teoreetiline maksumus, kui v6tta aluseks p2eva k6ige madalam tunnihind
    result['NP min [€]'] = (result['Elektrienergia kulu [kWh]'] * (result['NordPool hind [s/kWh]'] + MARGINAAL) / 100 * 1.2).round(2)
    cols = [
        'EE leping [€]',
        'EE muutuv [€]',
        # 'NordPool hind [s/kWh]',
        # 'NP min [€]'
    ]
    v6rdlus = result[cols]
    result = v6rdlus.groupby([v6rdlus.index.get_level_values('Aasta'), v6rdlus.index.get_level_values('Kuu')]).sum()
    print('\n' + 'V6rdlus lepingu hind vs börsihind (ilma kuutasuta):')
    print(result)
    print(result.sum())

    # välistemperatuur vs NPS keskmine hind
    g = df.groupby(round(df['Actual outdoor temperature [°C]']))
    result = pd.concat([g['NordPool hind [s/kWh]'].mean()], axis=1).round(1)
    result.replace([np.inf, -np.inf], np.nan, inplace=True)
    result.dropna(inplace=True)
    result.to_csv('kontroll_actoutdtemp_vs_npsprice.csv')
    # print(result)

