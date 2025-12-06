import asyncio
import datetime as dt

# Kui on vaja Django mooduleid
if __name__ == "__main__":
    import os
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'aquarea.settings'
    django.setup()

import pandas as pd
from scipy import stats

from ajalugu.Aquarea import AquareaData

async def main():
    bda = AquareaData()
    df = bda.tunniandmed()
    return await asyncio.gather(
        *list(show_cop_analysis(df, temp) for temp in [-10, -5, 0, 5, 10])
    )

async def show_cop_analysis(
    df: pd.DataFrame, 
    temp: int
):
    """
    columns:
    'Zone1: Actual (water outlet/room/pool) temperature [°C]',
    'Zone2: Actual (water outlet/room/pool) temperature [°C]',
    'Actual tank temperature [°C]', 'Actual outdoor temperature [°C]',
    'Heat mode energy consumption [kW]', 'Tank mode energy consumption [kW]', 
    'Heat mode energy generation [kW]', 'Tank mode energy generation [kW]'],
    """
    # defineerime otsitava vahemiku
    filter = (
        (df['Heat mode energy consumption [kW]'] > 0) &
        (df['Heat mode energy generation [kW]'] > 0) &
        (df['Actual outdoor temperature [°C]'] == temp)
    )
    andmed = df[filter].copy()
    values = andmed['Heat mode energy generation [kW]'] / andmed['Heat mode energy consumption [kW]']
    andmed['cop'] = values
    andmed['date'] = andmed.apply(lambda row: dt.datetime(*row.name), axis = 1)
    andmed['date_ordinal'] = pd.to_datetime(andmed['date']).map(dt.datetime.toordinal)
    slope, intercept, r_value, p_value, std_err = stats.linregress(andmed['date_ordinal'], andmed['cop'])
    print(temp, f'{slope:.10f}')

if __name__ == '__main__':
    asyncio.run(main())
    # print()
    # print(f"r1: {r1}, r2: {r2}, r3: {r3}")