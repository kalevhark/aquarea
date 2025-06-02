# Lisab iga päev Aquarea andmefailile värsked andmed
# andmefail af.pickle
# lisatav fail nimekujuga Statistics_B197792584_20250430003508_20250511005836.csv
from datetime import datetime
from pathlib import Path, PurePath
import pickle

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
# DATA_DIR = PurePath.joinpath(BASE_DIR, 'static/app/data/')
DATA_DIR = PurePath.joinpath(BASE_DIR, '')
AF_FILE = PurePath.joinpath(DATA_DIR, 'af.pickle')

def check_af_file(data_dir):
    return sorted(Path(data_dir).glob('af.pickle'))

def check_new_datafile(data_dir):
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    today_str = f'{year}{month:02d}{day:02d}'
    return sorted(Path(data_dir).glob(f'Statistics_B197792584_??????????????_{today_str}??????.csv'))

def read_af_from_file(af_file_glob):
    af_file_name = af_file_glob[0]
    with open(af_file_name, 'rb') as f:
        # The protocol version used is detected automatically, so we do not have to specify it.
        af = pickle.load(f)
    return af

def read_df_from_file(new_datafile_glob):
    new_datafile_name = new_datafile_glob[0]
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

    df = pd.read_csv(
        new_datafile_name,
        delimiter=',',
        decimal='.',
        dtype=dtype,
        parse_dates=[0],
        date_format="%d.%b.%Y %H:%M:%S",
        usecols=cols,
    )
    df = df.set_index('Timestamp')
    return df

if __name__ == "__main__":
    print("Andmed kataloogis: ", DATA_DIR)
    af_file_glob = check_af_file(DATA_DIR) # kas eelnevad andmed on olemas
    new_datafile_glob = check_new_datafile(DATA_DIR) # kas uus andmefail on olemas
    if af_file_glob and new_datafile_glob:
        af = read_af_from_file(af_file_glob)
        print("Eelnev:", af.shape, af.index.min(), af.index.max())
        df = read_df_from_file(new_datafile_glob)
        af = pd.concat([af, df], axis=0)
        af = af[af.index.duplicated(keep='first')==False]  # Ühendame andmefreimid ja kõrvaldame duplikaadid
        print("Uuendatud:", af.shape, af.index.min(), af.index.max())
        # Kirjutame andmed pickle faili
        with open(AF_FILE, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(af, f, pickle.DEFAULT_PROTOCOL)
        
    