import aiohttp
import asyncio
from datetime import datetime, timedelta, timezone
import logging

from api_client import AquareaAPIClient
from const import (
    AQUAREA_USR,
    AQUAREA_PWD,
    AQUAREA_SELECTEDGWID
)
from core import AquareaClient, AquareaEnvironment
from data import (
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
from entities import DeviceImpl
# from statistics import Consumption, DateType

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
        device.temperature_outdoor,
    )
    print(
        device.zones[1].name, 
        device.zones[1].operation_status, 
        device.zones[1].temperature, 
        device.zones[1].heat_target_temperature,
        device.zones[1].eco,
        device.zones[1].comfort
    )
    print(
        device.zones[2].name, 
        device.zones[2].operation_status, 
        device.zones[2].temperature, 
        device.zones[2].heat_target_temperature,
        device.zones[2].eco,
        device.zones[2].comfort
    )
    print(
        device.tank.operation_status, device.tank.temperature, device.tank.target_temperature
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

# Küsib nädalaseadistuse andmed ja tagastab dict() vormingus
async def get_weekly_timer_data(
    client: AquareaAPIClient,
    device: DeviceImpl
):
    pass

async def main():
    async with aiohttp.ClientSession() as session:
        client = AquareaClient(
            username=AQUAREA_USR,
            password=AQUAREA_PWD,
            session=session,
            device_direct=True,
            refresh_login=True,
            environment=AquareaEnvironment.PRODUCTION,
        )
        
        # Or the device can also be retrieved by its long id if we know it:
        device = await client.get_device(
            device_id=AQUAREA_SELECTEDGWID, 
            # consumption_refresh_interval=timedelta(minutes=1)
        )
        
        await print_device_info(device)

        # consumption_list = await client.get_device_consumption(
        #     device.long_id,
        #     DateType.DAY,
        #     "20251102" # Use YYYYMM01 for month mode
        # )

        # for item in consumption_list:
        #     print(item.heat_consumption, item.tank_consumption)

        # await get_weekly_timer_data(client, device)

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
    asyncio.run(main())
    logger.info(f'Finished {datetime.now()}')
