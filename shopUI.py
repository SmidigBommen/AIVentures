class ShopUI:
    def __init__(self, shop):
        self.shop = shop

    def show_shop_menu(self, character):
        """Display the shop main menu and handle interactions."""
        shopping = True

        while shopping:
            print(f"\n=== {self.shop.name} ===")
            print(f"Your gold: {character.gold}")
            print("\nWhat would you like to do?")
            print("1. Buy items")
            print("2. Sell items")
            print("3. Leave shop")

            choice = input("Enter your choice (1-3): ")

            if choice == "1":
                self.show_buy_menu(character)
            elif choice == "2":
                self.show_sell_menu(character)
            elif choice == "3":
                print(f"\nThank you for visiting {self.shop.name}!")
                shopping = False
            else:
                print("Invalid choice. Please try again.")

    def show_buy_menu(self, character):
        """Display items for sale and handle purchases."""
        inventory = self.shop.get_inventory()

        if not inventory:
            print("\nThe shop has nothing for sale right now.")
            return

        print("\n=== Items For Sale ===")
        for i, item_data in enumerate(inventory):
            item = item_data["item"]
            price = item_data["price"]
            quantity = item_data["quantity"]

            # Format item details
            stock_status = f"In stock: {quantity}" if quantity > 0 else "Out of stock"
            print(f"{i + 1}. {item.name} - {price} gold - {stock_status}")
            print(f"   {item.description}")

        print(f"{len(inventory) + 1}. Return to main menu")

        # Get player choice
        try:
            choice = int(input("\nWhat would you like to buy? "))

            if choice == len(inventory) + 1:
                return

            if 1 <= choice <= len(inventory):
                success, message = self.shop.buy_item(choice - 1, character)
                print(message)
            else:
                print("Invalid choice.")
        except ValueError:
            print("Please enter a valid number.")

    def show_sell_menu(self, character):
        """Display character's inventory and handle selling items."""
        if not character.inventory:
            print("\nYou have nothing to sell.")
            return

        print("\n=== Your Inventory ===")
        for i, item in enumerate(character.inventory):
            sell_price = self.shop.calculate_sell_price(item)
            print(f"{i + 1}. {item.name} - Sell value: {sell_price} gold")
            print(f"   {item.description}")

        print(f"{len(character.inventory) + 1}. Return to main menu")

        # Get player choice
        try:
            choice = int(input("\nWhat would you like to sell? "))

            if choice == len(character.inventory) + 1:
                return

            if 1 <= choice <= len(character.inventory):
                success, message = self.shop.sell_item(choice - 1, character)
                print(message)
            else:
                print("Invalid choice.")
        except ValueError:
            print("Please enter a valid number.")