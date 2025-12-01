import aiohttp
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import time

from .api_client import AquareaAPIClient
from .const import (
    AQUAREA_USR,
    AQUAREA_PWD,
    AQUAREA_SELECTEDGWID
)
from .core import AquareaClient, AquareaEnvironment
from .data import (
    AQUAREA_SERVICE_DEVICES,
    AQUAREA_SERVICE_A2W_STATUS_DISPLAY,
    DeviceZone,
    DeviceZoneStatus,
    ForceDHW,
    ForceHeater,
    HolidayTimer,
    OperationStatus,
    PowerfulTime,
    QuietMode,
    SpecialStatus,
    UpdateOperationMode,
    ZoneTemperatureSetUpdate,
)
from .entities import DeviceImpl
from .statistics import Consumption, DateType

logger = logging.getLogger(__name__)

async def print_device_info(
    device: DeviceImpl
) -> None:
    """Print device info.
    :param device: Device
    """
    print(
        'Soojuspump:', device.device_name, device.device_id, # device.long_id,
    )
    print(
        'Outdoor:', device.temperature_outdoor,
    )
    for zone in [1, 2]:
        print(
            device.zones[zone].name, 
            device.zones[zone].operation_status, 
            device.zones[zone].temperature, 
            device.zones[zone].heat_target_temperature,
            device.zones[zone].eco,
            device.zones[zone].comfort
        )
    print(
        'Tank',
        device.tank.operation_status, 
        device.tank.temperature, 
        device.tank.target_temperature
    )

async def post_device_set_special_status(
        client: AquareaClient,
        device: DeviceImpl,
        special_status: SpecialStatus | None,
    ) -> None:
        if device.special_status == special_status: # status already active
            return
        special_status_temprature_set = {
            SpecialStatus.NORMAL: {
                'zoneStatus': [
                    {
                        'zoneId': 1,
                        'heatSet': 0, 
                        'coolSet': 0, 
                    },
                    {
                        'zoneId': 2,
                        'heatSet': 0, 
                        'coolSet': 0, 
                    },
                ]
            },
            SpecialStatus.ECO: {
                'zoneStatus': [
                    {
                        'zoneId': 1,
                        'heatSet': device.zones[1].eco.heat,
                        'coolSet': device.zones[1].eco.cool, 
                    },
                    {
                        'zoneId': 2,
                        'heatSet': device.zones[2].eco.heat,
                        'coolSet': device.zones[2].eco.cool, 
                    },
                ]
            },
            SpecialStatus.COMFORT: {
                'zoneStatus': [
                    {
                        'zoneId': 1,
                        'heatSet': device.zones[1].comfort.heat,
                        'coolSet': device.zones[1].comfort.cool, 
                    },
                    {
                        'zoneId': 2,
                        'heatSet': device.zones[2].comfort.heat,
                        'coolSet': device.zones[2].comfort.cool, 
                    },
                ]
            }
        }
        """Post device operation update."""
        data = {
            "apiName": "/remote/v1/api/devices",
            "requestMethod": "POST",
            "bodyParam": {
                "gwid": device.long_id,
                "specialStatus": special_status.value,
                'zoneStatus': special_status_temprature_set[special_status]['zoneStatus']
            },
            
        }
        
        await client._api_client.request(
            "POST",
            "remote/v1/app/common/transfer",
            json=data,
            throw_on_error=True,
        )

        
async def post_device_force_dhw(
    client: AquareaClient, 
    device: DeviceImpl, 
    force_dhw: ForceDHW
) -> None:
    """Post force DHW command."""
    data = {
        "apiName": f"/{AQUAREA_SERVICE_DEVICES}", # "/remote/v1/api/devices",
        "requestMethod": "POST",
        "bodyParam": {"gwid": device.long_id, "forceDHW": force_dhw.value},
    }

    await client._api_client.request(
        "POST",
        "remote/v1/app/common/transfer",
        json=data,
        throw_on_error=True,
    )


async def post_device_tank_operation_status(
    client: AquareaClient, 
    device: DeviceImpl,
    new_operation_status: OperationStatus,
) -> None:
    """Post device tank operation status."""
    if new_operation_status == device.tank.operation_status:
         return
    zone_status_list = []
    for zone in device.zones:
        zone_status_list.append(
            {
                "zoneId": device.zones[zone].zone_id,
                "operationStatus": device.zones[zone].operation_status.value,
            }
        )

    data = {
        "apiName": f"/{AQUAREA_SERVICE_DEVICES}", # "/remote/v1/api/devices",
        "requestMethod": "POST",
        "bodyParam": {
            "gwid": device.long_id,
            "zoneStatus": zone_status_list,
            "tankStatus": {"operationStatus": new_operation_status.value},
        },
    }

    await client._api_client.request(
        "POST",
        url="remote/v1/app/common/transfer",  # Specific URL for transfer API
        json=data,
        throw_on_error=True,
    )

async def get_status():
    async with aiohttp.ClientSession() as session:
        client = AquareaClient(
            username=AQUAREA_USR,
            password=AQUAREA_PWD,
            session=session,
            device_direct=True,
            refresh_login=True,
            environment=AquareaEnvironment.PRODUCTION,
        )
        
        tries = 3
        while tries > 0:
            try:
                device = await client.get_device(
                    device_id=AQUAREA_SELECTEDGWID, 
                    # consumption_refresh_interval=timedelta(minutes=1)
                )
                break
            except:
                tries -= 1
                time.sleep(10)

        
        # await print_device_info(device)
        return device

def get_tank_status():
    device = asyncio.run(get_status())
    return {
        'device_operation_status': device.operation_status,
        'temperature_outdoor': device.temperature_outdoor,
        'tank_operation_status': device.tank.operation_status, 
        'tank_temperature': device.tank.temperature, 
        'tank_target_temperature': device.tank.target_temperature
    }

def unknown():
    special_status = SpecialStatus.NORMAL
    
    # await post_device_set_special_status(
    #     client=client,
    #     device=device,
    #     special_status=special_status,
    # )

    new_operation_status = OperationStatus.ON

    # await post_device_tank_operation_status(
    #     client=client,
    #     device=device,
    #     new_operation_status=new_operation_status,
    # )

    # await post_device_force_dhw(
    #     client=client,
    #     device=device,
    #     force_dhw=ForceDHW.OFF,
    # )


if __name__ == "__main__":
    logging.basicConfig(filename='aioaquarea.log', level=logging.INFO)
    logger.info(f'Started {datetime.now()}')
    # asyncio.run(get_status())
    # unknown()
    logger.info(f'Finished {datetime.now()}')
