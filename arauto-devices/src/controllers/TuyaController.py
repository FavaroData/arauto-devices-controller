import tinytuya
from Device import Device
from controllers.DeviceController import DeviceController, DeviceControllerError


class TuyaDeviceController(DeviceController):
    def turn_on(self, device: Device) -> None:
        self._set_switch(device, True)

    def turn_off(self, device: Device) -> None:
        self._set_switch(device, False)

    def get_status(self, device: Device) -> dict:
        d = self._connect(device)
        result = d.status()
        if "Error" in result:
            raise DeviceControllerError(result["Error"])
        return result

    def is_online(self, device: Device) -> bool:
        try:
            d = self._connect(device)
            result = d.status()
            return isinstance(result, dict) and "Error" not in result
        except DeviceControllerError:
            return False

    def _set_switch(self, device: Device, ligar: bool) -> None:
        d = self._connect(device)
        result = d.set_status(ligar, switch=1)
        if isinstance(result, dict) and "Error" in result:
            raise DeviceControllerError(result["Error"])

    def _connect(self, device: Device) -> tinytuya.Device:
        try:
            d = tinytuya.Device(
                dev_id=device.id,
                address=device.ip,
                local_key=device.local_key,
                version=device.version,
            )
        except RuntimeError as e:
            raise DeviceControllerError(f"Dispositivo não encontrado na rede: {e}")

        d.set_socketPersistent(True)
        return d