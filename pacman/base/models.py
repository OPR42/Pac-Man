from pydantic import BaseModel, ConfigDict, Field


class Defaults(BaseModel):
    allow_raylib_shapes: bool = True
    allow_terminal_display: bool = True

    audio_volume_step: float = 0.05

    actors_blink_min_delay: float = 1.5
    actors_blink_max_delay: float = 5.0
    actors_blink_duration: float = 0.5

    background_actors_quantity: int = 21
    background_actors_size: int = 20
    background_actors_min_speed: int = 80

    banner_min_interval: float = 5.0
    banner_max_interval: float = 15.0

    duration_superpacgum: float = 10.0
    duration_superpacgum_end_warning: float = 2.0
    duration_sage: float = 20.0
    duration_bomb_detonation: float = 3.0

    game_title: str = "The Adventures of Pac-Man Across the 3rd Dimension"
    game_title_includes_resolution: bool = False

    gamepad_stick_trigger: float = 0.50
    gamepad_stick_release: float = 0.20

    graphics_base_width: int = 1600
    graphics_base_height: int = 900
    graphics_base_font_size: int = 20
    graphics_base_margin: int = 4
    graphics_base_frame_thick: int = 2

    gumcharmer_speed: float = 3.0
    gumcharmer_threshold_ratio: float = 0.50

    highscores_max_entries: int = 20
    highscores_display_entries: int = 10
    highscores_corrupted: int = -999_999_999

    hud_livebox_capacity: int = 20
    hud_livebox_resize_factor: float = 1.0
    hud_livebox_halo_duration: float = 0.20
    hud_livebox_stabilization_timeout: float = 5.0

    interludes_char_delay: float = 0.008
    interludes_char_fade: float = 0.960
    interludes_block_pause: float = 0.320
    interludes_space_factor: float = 1.50

    inventory_sage_radius: int = 4
    inventory_bomb_radius: int = 6

    logbook_min_height: int = 34

    maze_min_width: int = 14
    maze_min_height: int = 10

    pacman_base_mouth_opening: float = 0.50
    pacman_min_mouth_opening: float = 0.25
    pacman_max_mouth_opening_to_pg: float = 1.00
    pacman_max_mouth_opening_to_spg: float = 1.25
    pacman_mouth_close_duration: float = 0.15
    pacman_max_speed: float = 4.0

    playername_keyboard_alphanumeric_hints: bool = False

    terminal_base_wait: float = 0.0005

    text_monospace_width_ratio: float = 0.5125
    text_line_spacing: int = 2

    texture_generate_size: int = 1024
    texture_generate_seed: int = 42
    texture_brushed_metal_rgb: tuple[int, int, int] = (127, 127, 127)
    texture_gunmetal_rgb: tuple[int, int, int] = (36, 37, 38)
    texture_lightwood_rgb: tuple[int, int, int] = (225, 181, 152)
    texture_wood_rgb: tuple[int, int, int] = (125, 85, 55)
    texture_darkerwood_rgb: tuple[int, int, int] = (47, 37, 35)


class LevelConfig(BaseModel):
    width: int = 12
    height: int = 10


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data_dir: str = "data"
    highscore_filename: str = "hall_of_fame.json"
    window_width: int = 1600
    window_height: int = 900
    window_resizeable: bool = True
    window_maximized: bool = False
    window_position: str = "right"
    frame_and_banner: bool = True
    master_volume: int = 100
    music_volume: int = 100
    sound_volume: int = 100
    language: str = "english"
    hints: bool = True
    hints_delay: float = 0.5
    main_menu_idle_time: int = 30
    main_menu_idle_visitor_min_time: int = 30
    main_menu_idle_visitor_max_time: int = 60
    disable_transitions: bool = False
    lives: int = 3
    pts_pacgum: int = 10
    pts_super_pacgum: int = 50
    pts_ghost: int = 200
    pts_bonus1: int = 400
    pts_bonus2: int = 500
    pts_bonus3: int = 600
    pts_bonus4: int = 700
    pts_bonus5: int = 800
    pts_bonus6: int = 900
    new_life_threshold: int = 5000
    level_max_time: int = 90
    timeout_consequence: str = "speeding_ghosts"
    seed: int = 42
    levels: list[LevelConfig] = Field(default_factory=lambda: [
            LevelConfig(width=15, height=10),
            LevelConfig(width=16, height=10),
            LevelConfig(width=16, height=11),
            LevelConfig(width=17, height=11),
            LevelConfig(width=17, height=12),
            LevelConfig(width=18, height=12),
            LevelConfig(width=18, height=13),
            LevelConfig(width=19, height=13),
            LevelConfig(width=19, height=14),
            LevelConfig(width=20, height=14),
            LevelConfig(width=20, height=15),
            LevelConfig(width=21, height=15),
            LevelConfig(width=21, height=16),
            LevelConfig(width=22, height=16),
            LevelConfig(width=22, height=17),
        ]
    )


class GameState(BaseModel):
    status: int = 0
    skin: int = 0
    starttime: float = 0.0
    runtime: float = 0.0
    frame_and_banner: bool = True
    nb_levels: int = 0
    level: int = 0
    seed: int = 42
    maze_width: int = 0
    maze_height: int = 0
    cell_size: int = 0
    character_size: int = 0
    start_pos: tuple[int, int] = (0, 0)
    score: int = 0
    lives_init: int = 0
    lives_cur: int = 0
    lives_gained: int = 0
    pacgum_init: int = 0
    pacgum_cur: int = 0
    pacgum_eaten: int = 0
    suppacgum_init: int = 0
    suppacgum_cur: int = 0
    suppacgum_eaten: int = 0
    item_init: int = 0
    item_cur: int = 0
    item_eaten: int = 0
    time_init: float = 0.0
    time_cur: float = 0.0
    on_timeout: int = 0


class PointsTable(BaseModel):
    pacgum: int = 0
    super_pacgum: int = 0
    ghost: int = 0
    bonus1: int = 0
    bonus2: int = 0
    bonus3: int = 0
    bonus4: int = 0
    bonus5: int = 0
    bonus6: int = 0
    new_life: int = 0


class CharacterState(BaseModel):
    name: str = ""
    displayed: bool = False
    pos_x: int = 0
    pos_y: int = 0
    cell_x: int = 0
    cell_y: int = 0
    direction: int = 0
    activity: int = 0
    status: int = 1
    cycle: float = 0.25
    blink_start_time: float | None = None
    blink_next_time: float | None = None
    max_speed: float = 0.0
    last_hor_dir: str = "right"
    goal_cell_x: int = 0
    goal_cell_y: int = 0
    next_cell_x: int = -1
    next_cell_y: int = -1
    previous_cell_x: int = -1
    previous_cell_y: int = -1
    reverse_pending: bool = False


class CheatsTable(BaseModel):
    unlocked: bool = False
    invulnerable: bool = False
    sprinter: bool = False
    outatime: bool = False
    walldenier: bool = False
    jackhammer: bool = False
    gumcharmer: bool = False
    gluttonous: bool = False


class Score(BaseModel):
    name: str
    score: int
    corrupted: bool = False


class PacgumState(BaseModel):
    """Store a Pacgum state."""
    superpacgum: bool = False
    pos_x: float = 0.0
    pos_y: float = 0.0
    path: list[tuple[float, float]] = Field(default_factory=list)
    path_index: int = 0


class HUDLifeState(BaseModel):
    pos_x: float = 0.0
    pos_y: float = 0.0
    vel_x: float = 0.0
    vel_y: float = 0.0
    angle: float = 0.0
    angular_speed: float = 0.0
    stable: bool = False
    spawning: bool = True
    despawning: bool = False
    halo_start_time: float | None = None


class LogEvent(BaseModel):
    """
    Carry structured information from processing code
    to the user interface.
    """
    source: str = ""
    type: str = ""
    message: str = ""
    duration: float = 0.0
    text_var: str = ""
    message_end: str = ""
    value: float = 0.0
    left_box: str = ""
    right_box: str = ""
    int_a: int = 0
    int_b: int = 0
    int_c: int = 0
    float_a: float = 0.0
    float_b: float = 0.0
    float_c: float = 0.0
    fields: list[str] = Field(default_factory=list)
