from emulator_client.adb_client import ADBClient
from emulator_client.game_control.tiles import get_coords_from_tile
import time

class GameClient:
    def __init__(self, serial: str):
        self.adb_client = ADBClient(serial)
        self.adb_client.open()

    def enter_clan_chat(self):
        self.adb_client.tap(480, 1215)
        time.sleep(1)
        self.adb_client.tap(685, 125)
        
    def create_challenge(self):
        self.adb_client.tap(295, 1080)
        time.sleep(1)
        self.adb_client.tap(360, 360)
    
    def accept_challenge(self):
        self.adb_client.tap(565, 940)
        
    def exit_game(self):
        self.adb_client.tap(360, 1160)
        
    def select_card(self, card_position: int):
        x_pos = 155 + (card_position - 0.5) * 137.5
        self.adb_client.tap(x_pos, 1150)
        
    def click_tile(self, x: int, y: int):
        self.adb_client.tap(*get_coords_from_tile(x, y))
        
    def place_card_on_tile(self, card_position: int, x: int, y: int):
        self.select_card(card_position)
        self.click_tile(x, y)