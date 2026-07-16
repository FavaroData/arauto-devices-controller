import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from DevicesRepository import DeviceRepository
from controllers.TuyaController import TuyaDeviceController

repo = DeviceRepository(Path(__file__).parent.parent / "src" / "devices.json")
controller = TuyaDeviceController()

device = repo.get_by_name("quarto")  # troque pelo nome real no seu devices.json

print("Status antes:", controller.get_status(device))
controller.turn_on(device)
print("Ligado!")