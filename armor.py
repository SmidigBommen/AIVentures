from equipment import Equipment
from equipmentType import EquipmentType

class Armor(Equipment):
    def __init__(self, name: str, base_ac: int, category: str):
        super().__init__(name, EquipmentType.ARMOR, {})
        self.base_ac = base_ac # Light and Medium should be added to with dex bonus..
        self.category = category  # "Light", "Medium", or "Heavy"


        