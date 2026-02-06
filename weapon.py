from equipment import Equipment
from equipmentType import EquipmentType

class Weapon(Equipment):
    def __init__(self, name: str, damage_die: int, damage_type: str, category: str, properties=None,
                 damage_dice_count=1, description=""):
        super().__init__(name, EquipmentType.WEAPON, {})
        self.description = description
        self.damage_die = damage_die
        self.damage_type = damage_type
        self.category = category  # "Simple" or "Martial"
        self.properties = properties or []
        self.damage_dice_count = damage_dice_count  # Default is 1, but some weapons like greatsword use 2d6 (two dice)

    @property
    def is_ranged(self):
        return "ammunition" in self.properties

    @property
    def is_finesse(self):
        return "finesse" in self.properties
