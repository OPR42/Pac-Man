class RenderColors:
    """ Define Render color codes. """
    BLANK = (0, 0, 0, 0)

    BASE_RED = (255, 0, 0, 255)
    BASE_BROWN = (162, 115, 76, 255)
    BASE_BLUE = (0, 0, 170, 255)
    BASE_CYAN = (51, 199, 222, 255)
    BASE_WHITE = (191, 191, 191, 255)
    BASE_BR_BROWN = (255, 255, 85, 255)
    BASE_BR_PURPLE = (192, 97, 203, 255)
    BASE_BR_CYAN = (0, 255, 255, 255)
    BASE_BR_WHITE = (255, 255, 255, 255)
    BASE_BLACK = (0, 0, 0, 255)
    BASE_DARK_GREY = (79, 79, 79, 255)
    BASE_DARKER_GREY = (47, 47, 47, 255)
    BASE_DARKERER_GREY = (31, 31, 31, 255)

    BLUE42 = (16, 32, 96, 255)
    DEEP_PURPLE = (54, 18, 72, 255)
    BLACK_LIGHTGLASS = (0, 0, 0, 63)
    BLACK_GLASS = (0, 0, 0, 127)
    BLACK_MEDIUMGLASS = (0, 0, 0, 159)
    BLACK_DARKGLASS = (0, 0, 0, 191)
    WHITE_GLASS = (255, 255, 255, 127)
    PACMAN_YELLOW = (223, 195, 55, 255)
    PACMAN_YELLOW_TRANSPARENT = (223, 195, 55, 63)
    BLINKY_RED = (240, 24, 35, 255)
    PINKY_PINK = (253, 189, 222, 255)
    INKY_CYAN = (2, 255, 226, 255)
    CLYDE_ORANGE = (255, 190, 69, 255)
    EYE_BLUE = (0, 107, 192, 255)
    SCARED_GHOST_BLUE = (10, 69, 220, 255)
    BLOODY_EYE_SALMON = (248, 198, 186, 255)
    SCARED_MOUTH_DARK_SALMON = (124, 99, 93, 255)
    ETHEREAL_GHOST_BODY = (10, 69, 220, 63)
    DISGUSTED_GHOST_GREEN = (38, 201, 109, 255)
    PACGUM = (247, 199, 163, 255)
    WALL_STD = (46, 46, 254, 255)
    PAPER = (241, 237, 226, 255)
    PAPER_OLD = (211, 173, 124, 255)
    BLANK = (0, 0, 0, 0)
    PORTAL_BLUE = (0, 140, 255, 255)
    PORTAL_ORANGE = (255, 140, 0, 255)
    PORTAL_YELLOW_HALO = (222, 199, 51, 255)
    HOURGLASS_BULB = (39, 39, 59, 255)
    SAND = (211, 173, 124, 255)
    SAND_SPREAD = (211, 173, 124, 63)
    LIGHT_WHITE = (221, 221, 221, 255)
    LIGHT_BEIGE = (255, 239, 191, 255)
    LIGHTER_BEIGE = (255, 247, 223, 255)
    GREY = (127, 127, 127, 255)
    GREY_TRANSPARENT = (127, 127, 127, 63)
    DARKGREY_TRANSPARENT = (79, 79, 79, 63)
    WALL_SKIN_1 = (254, 184, 150, 255)
    EDGE_SKIN_1 = (221, 14, 3, 255)
    GROUND_SKIN_2 = (118, 61, 4, 255)
    WALL_SKIN_2 = (0, 110, 65, 255)
    EDGE_SKIN_2 = (79, 50, 35, 255)
    GRAD1_SKIN_2 = (70, 166, 208, 255)
    GRAD2_SKIN_2 = (82, 133, 160, 255)
    GRAD1_SKIN_3 = (247, 166, 208, 255)
    GRAD2_SKIN_3 = (211, 76, 134, 255)
    BOWTIE_RED = (155, 25, 45, 255)
    JAIL_YELLOW = (251, 242, 89, 255)
    BLAST_OUT = (225, 77, 32, 255)
    BLAST_MED = (255, 223, 45, 255)
    BLAST_CNT = (255, 255, 255, 255)
    CUBE_FRAME = (229, 229, 229, 255)
    CUBE_BOX = (127, 131, 132, 255)
    CUBE_LINES = (192, 97, 203, 255)
    CUBE_PANEL = (63, 63, 63, 255)
    STETSON_IVORY = (242, 234, 211, 255)
    SLIME_GREEN = (105, 220, 55, 255)
    HOURGLASS_WOOD = (125, 85, 55, 255)
    BOMB_VIOLET = (105, 55, 175, 255)

    @staticmethod
    def scale_rgb(rgb: tuple[int, int, int, int],
                  factor: float) -> tuple[int, int, int, int]:
        """ Scale RGB components by the specified factor. """
        return (max(0, min(255, int(rgb[0] * factor))),
                max(0, min(255, int(rgb[1] * factor))),
                max(0, min(255, int(rgb[2] * factor))),
                max(0, min(255, int(rgb[3]))))

    @staticmethod
    def mix_rgba(rgb_a: tuple[int, int, int, int],
                 rgb_b: tuple[int, int, int, int],
                 weight_a: float) -> tuple[int, int, int, int]:
        if not rgb_a or not rgb_b or not weight_a:
            return (127, 127, 127, 127)

        wa = min(1.0, max(0.0, weight_a))
        wb = 1.0 - wa

        ra, ga, ba, aa = rgb_a
        rb, gb, bb, ab = rgb_b
        return (max(0, min(255, round(ra * wa + rb * wb))),
                max(0, min(255, round(ga * wa + gb * wb))),
                max(0, min(255, round(ba * wa + bb * wb))),
                max(0, min(255, round(aa * wa + ab * wb))))

    @staticmethod
    def scale_alpha(rgb: tuple[int, int, int, int],
                    factor: float) -> tuple[int, int, int, int]:
        """ Scale Alpha component by the specified factor. """
        return (max(0, min(255, int(rgb[0]))),
                max(0, min(255, int(rgb[1]))),
                max(0, min(255, int(rgb[2]))),
                max(0, min(255, int(rgb[3] * factor))))
