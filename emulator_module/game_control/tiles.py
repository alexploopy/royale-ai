import math

def get_coords_from_tile(x: int, y: int) -> tuple[int, int]:
    """
    Get the coordinates of a tile in the game.

    Args:
        x (int): The x coordinate of the tile.
        y (int): The y coordinate of the tile.

    Returns:
        tuple[int, int]: The coordinates of the tile.
    """
    
    OFFSET_X = 50
    OFFSET_Y = 100
    
    TILE_WIDTH = 34.50
    TILE_HEIGHT = 27.5

    return (x - 0.5) * TILE_WIDTH + OFFSET_X, ((32 + 1) - y - 0.5) * TILE_HEIGHT + OFFSET_Y

def is_tile_valid(x: int, y: int, l_tower_alive: bool = True, r_tower_alive: bool = True) -> bool:
    """
    Check if the coordinates are valid for a given tile for a troop placement.

    Args:
        x (int): The x coordinate of the tile.
        y (int): The y coordinate of the tile.
        l_tower_alive (bool, optional): Whether the left tower is alive.
        r_tower_alive (bool, optional): Whether the right tower is alive.

    Returns:
        bool: Whether the coordinates are valid.
    Notes:
        - Bottom-Right is (1, 1)
        - Although the game blocks placments on invalid tiles, we want to punish the model for placing on invalid tiles.
    """
    
    if x < 0 or y < 0:
        # Cannot place on the top rows since king tower is there
        return False
    if x > 18 or y > 21:
        return False
    if (y == 1) and (x <= 6 or x > 12):
        # Bottom row, only tiles behind King Tower are valid
        return False
    if (y == 15 or y == 18) and (x == 1 or x == 18):
        # River corner bump
        return False
    if (y == 16 or y == 17) and (x != 4 or x != 15):
        # River, must be on bridge
        return False
    if l_tower_alive and (y > 15 and x <= 9):
        return False
    if r_tower_alive and (y > 15 and x >= 10):
        return False
    
    return True