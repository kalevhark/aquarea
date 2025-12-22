#
# Aquarea soojuspumba targaks juhtimiseks
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-wiki-app/tasks.py
import datetime as dt
import logging
from pathlib import Path
from zoneinfo import ZoneInfo
import holidays # Vajab installimist: pip install holidays

OUTDOOR_HEAT_EFFICENCY_TEMP = 0 # õhutemperatuur, millest alates COP>=2,9
OUTDOOR_TANK_EFFICENCY_TEMP = 5 # õhutemperatuur, millest alates COP>=1,6
DHW_TANK_GAP_NIGHT = 4 # millisest temperatuurilangusest alates hakatakse kütma tarbevett soodusajal
DHW_TANK_GAP_DAY = 6 # millisest temperatuurilangusest alates hakatakse kütma tarbevett normaalajal
LEDVANCE = 1 # Milline smartswitch on boileri elektritoide

EST_TZ = ZoneInfo("Europe/Tallinn")

# Kui on vaja Django mooduleid
if __name__ == "__main__":
    import os
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'aquarea.settings'
    django.setup()

from aioaquarea.views import get_tank_status
from app.utils import ledvance_util

logger = logging.getLogger(__name__)

def on_enefit_soodusaeg(
        dt_now: dt.datetime = dt.datetime.now(EST_TZ)
    ) -> bool:
    
    # Saame Eesti riigipühad
    ee_holidays = holidays.EE()
    
    # Tingimused
    is_weekend = dt_now.weekday() >= 5
    is_holiday = dt_now in ee_holidays
    is_night_hours = dt_now.hour >= 22 or dt_now.hour < 7
    
    # Kui on nädalavahetus VÕI riigipüha VÕI ööaeg -> Soodus
    if is_weekend or is_holiday or is_night_hours:
        # tariff = "ÖÖTARIIF (Soodne)"
        is_cheap = True
    else:
        # tariff = "PÄEVATARIIF (Kallis)"
        is_cheap = False
        
    # print(f"Kell on: {now.strftime('%H:%M')}")
    # print(f"Tariif: {tariff}")
    
    # Kui on riigipüha, prindime selle nime
    # if is_holiday:
    #     print(f"Püha: {ee_holidays.get(now)}")

    return is_cheap
    
def dhw_gap_correction(
    dt_now: dt.datetime
) -> int:
    """Kui algamas v6i l6ppemas on soodusaeg, siis korrigeerib max temperatuuri v2lpa"""
    # Kontrollime kas tunni aja jooksul algab soodusaeg
    if on_enefit_soodusaeg(dt_now) == False and on_enefit_soodusaeg(dt_now + dt.timedelta(hours=1)) == True:
        return +1
    # Kontrollime kas tunni aja jooksul l6peb soodusaeg
    if on_enefit_soodusaeg(dt_now) == True and on_enefit_soodusaeg(dt_now + dt.timedelta(hours=1)) == False:
        return -1
    return 0

def change_ledvance_status(
    tank_status: dict, 
    ledvance_status: dict
) -> None:
    if isinstance(tank_status, dict):
        dhw_gap = DHW_TANK_GAP_NIGHT if on_enefit_soodusaeg(dt.datetime.now(EST_TZ)) else DHW_TANK_GAP_DAY
        # Korrigeerime, kui soodusaja algus/l6pp tunni aja jooksul
        dhw_gap = dhw_gap + dhw_gap_correction(dt.datetime.now(EST_TZ))

        # Aquarea registreeritud välistemperatuur
        outdoorNow = tank_status['temperature_outdoor']
        
        # Aquarea tank hetkenäitajad
        # operation_status = tank_status['device_operation_status']
        temperature_now = tank_status['tank_temperature']
        heat_set = tank_status['tank_target_temperature']
        heat_max = heat_set + DHW_TANK_GAP_DAY # kui boileri temperatuur > soovitud temp + vahe
        # Arvutame soovitud ja hetke temperatuuri erinevuse
        gap = heat_set - temperature_now
        if ledvance_status['dps']['1']: # Kui LDV on sisselylitatud
            if temperature_now >= heat_max:
                ledvance_util.turnoff(ledvance=LEDVANCE)  # lülitame ledvance v2lja
                # print('LDV off')
                logger.info(f'LDV off: {temperature_now}>{heat_max}')
                return
        
        if (outdoorNow < OUTDOOR_TANK_EFFICENCY_TEMP): # Kui v2listemperatuur on v2iksem Aquarea tarbevee efektiivsest tootmistemperatuuris (COP < 1)
            if (gap > dhw_gap):
                ledvance_util.turnon(ledvance=LEDVANCE, hours=1) # lülitame ledvance sisse
                # print('LDV on=1h')
                logger.info(f'LDV on=1h: {temperature_now}->{heat_set}>{dhw_gap}')
            else:
                logger.info(f'LDV no action: {temperature_now}->{heat_set}<{dhw_gap}')
        else:
            logger.info(f'LDV no action: välistemperatuur {outdoorNow}>={OUTDOOR_TANK_EFFICENCY_TEMP}')

def main():
    # Define the path
    log_file_path = Path("logs/dhw_tank.log")
    # 1. Create directory (and parents) if they don't exist
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    # 2. Configure logging
    logging.basicConfig(filename=log_file_path, level=logging.INFO)

    logger.info(f'Started {dt.datetime.now(EST_TZ)}')
    
    try:
        tank_status = get_tank_status()
        logger.info(f'DHW tank status: {tank_status}')
    except Exception as e:
        tank_status = None
        logger.error(f'DHW tank status: error {e}')

    try:
        ledvance_status = ledvance_util.status(ledvance=LEDVANCE)
        logger.info(f'Ledvance status: {ledvance_status}')
    except Exception as e:
        ledvance_status = None
        logger.error(f'Ledvance status: error {e}')
    
    if all([tank_status, ledvance_status]):
        change_ledvance_status(tank_status, ledvance_status)
    logger.info(f'Finished {dt.datetime.now(EST_TZ)}')

if __name__ == '__main__':
    main()
    
