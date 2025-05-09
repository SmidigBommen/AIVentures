from items import HealingPotion


class Shop:
    def __init__(self, name="General Store"):
        self.name = name
        self.inventory = []
        self.setup_default_inventory()

    def setup_default_inventory(self):
        """Set up default shop inventory with basic items."""
        # Add basic healing potions
        self.add_item(HealingPotion("Minor Healing Potion", 5), 10)
        self.add_item(HealingPotion("Healing Potion", 10), 25)
        self.add_item(HealingPotion("Greater Healing Potion", 20), 50)

    def add_item(self, item, price):
        """Add an item to the shop inventory with its price."""
        self.inventory.append({
            "item": item,
            "price": price,
            "quantity": 5  # Default stock quantity
        })

    def get_inventory(self):
        """Get the current shop inventory."""
        return self.inventory

    def buy_item(self, index, character):
        """Handle a character buying an item from the shop."""
        if index < 0 or index >= len(self.inventory):
            return False, "Invalid item selection."

        item_data = self.inventory[index]

        # Check if item is in stock
        if item_data["quantity"] <= 0:
            return False, f"Sorry, {item_data['item'].name} is out of stock."

        # Check if character has enough gold
        if character.gold < item_data["price"]:
            return False, f"You don't have enough gold. You need {item_data['price']} gold."

        # Process the purchase
        character.gold -= item_data["price"]
        character.add_item(item_data["item"])
        item_data["quantity"] -= 1

        return True, f"You purchased {item_data['item'].name} for {item_data['price']} gold."

    def sell_item(self, item_index, character):
        """Handle a character selling an item to the shop."""
        if item_index < 0 or item_index >= len(character.inventory):
            return False, "Invalid item selection."

        item = character.inventory[item_index]

        # Calculate sell price (typically half of buy price or less)
        sell_price = self.calculate_sell_price(item)

        # Process the sale
        character.gold += sell_price
        character.inventory.pop(item_index)

        return True, f"You sold {item.name} for {sell_price} gold."

    def calculate_sell_price(self, item):
        """Calculate the sell price for an item (typically 50% of buy price)."""
        # Check if we have this item in our inventory to get the base price
        for item_data in self.inventory:
            if type(item) == type(item_data["item"]) and item.name == item_data["item"].name:
                return max(1, item_data["price"] // 2)  # At least 1 gold

        # Default pricing if item not in shop inventory
        if isinstance(item, HealingPotion):
            # Estimate based on healing amount
            return max(1, item.healing_amount // 2)

        # Fallback price
        return 1
