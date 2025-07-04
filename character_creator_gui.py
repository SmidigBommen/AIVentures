from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, Select, Input, Label
from textual.screen import Screen
import json

# Load data at module level
with open("json/races.json") as f:
    RACES_DATA = json.load(f)
with open("json/classes_properties.json") as f:
    CLASSES_DATA = json.load(f)


class CharacterCreationScreen(Screen):
    """Screen for creating a new character"""

    def __init__(self):
        super().__init__()
        self.character_name = ""
        self.selected_race = ""
        self.selected_class = ""

    def compose(self) -> ComposeResult:
        """Create the character creation interface"""

        yield Container(
            Static("Create Your Character", classes="title"),

            # Character Name Input
            Vertical(
                Label("Character Name:"),
                Input(placeholder="Enter your character's name", id="name_input"),
                classes="input-group"
            ),

            # Race Selection
            Vertical(
                Label("Race:"),
                Select(
                    [(race, race) for race in RACES_DATA.keys()],
                    prompt="Choose a race",
                    id="race_select"
                ),
                Static("", id="race_description"),
                classes="input-group"
            ),

            # Class Selection
            Vertical(
                Label("Class:"),
                Select(
                    [(class_name, class_name) for class_name in CLASSES_DATA.keys()],
                    prompt="Choose a class",
                    id="class_select"
                ),
                Static("", id="class_description"),
                classes="input-group"
            ),

            # Buttons
            Horizontal(
                Button("Create Character", variant="primary", id="create_btn"),
                Button("Cancel", variant="error", id="cancel_btn"),
                classes="button-group"
            ),

            classes="character-creator"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle name input changes"""
        if event.input.id == "name_input":
            self.character_name = event.value

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle race/class selection changes"""
        if event.select.id == "race_select" and event.value:
            self.selected_race = event.value
            # Show race bonuses
            race_stats = RACES_DATA[event.value]
            bonuses = [f"{stat.replace('_bonus', '').title()}: +{bonus}"
                       for stat, bonus in race_stats.items() if bonus > 0]
            self.query_one("#race_description").update(f"Bonuses: {', '.join(bonuses)}")

        elif event.select.id == "class_select" and event.value:
            self.selected_class = event.value
            # Show class info
            class_info = CLASSES_DATA[event.value]
            hit_die = class_info.get("hit_die", 8)
            primary = class_info.get("primary_ability", "Unknown")
            self.query_one("#class_description").update(
                f"Hit Die: d{hit_die}, Primary Ability: {primary}"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "create_btn":
            self.create_character()
        elif event.button.id == "cancel_btn":
            self.app.pop_screen()

    def create_character(self) -> None:
        """Validate and create the character"""
        if not self.character_name.strip():
            self.notify("Please enter a character name", severity="error")
            return
        if not self.selected_race:
            self.notify("Please select a race", severity="error")
            return
        if not self.selected_class:
            self.notify("Please select a class", severity="error")
            return

        # Character is valid, close screen and return data
        character_data = {
            "name": self.character_name.strip(),
            "race": self.selected_race,
            "class": self.selected_class
        }
        self.dismiss(character_data)


class CharacterCreatorApp(App):
    """Simple app to test the character creator"""

    CSS = """
    .title {
        dock: top;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .character-creator {
        align: center middle;
        width: 60;
        height: auto;
        margin: 2;
    }

    .input-group {
        margin-bottom: 1;
        width: 100%;
    }

    .button-group {
        dock: bottom;
        width: 100%;
        height: auto;
        margin-top: 2;
    }

    Button {
        margin: 0 1;
    }

    Select {
        width: 100%;
    }

    Input {
        width: 100%;
    }
    """

    def on_mount(self) -> None:
        """Show character creation screen on startup"""
        self.push_screen(CharacterCreationScreen(), self.character_created)

    def character_created(self, character_data) -> None:
        """Handle character creation completion"""
        if character_data:
            self.notify(
                f"Created character: {character_data['name']} ({character_data['race']} {character_data['class']})")
            # Here you would integrate with your existing CharacterFactory
        else:
            self.notify("Character creation cancelled")


if __name__ == "__main__":
    app = CharacterCreatorApp()
    app.run()