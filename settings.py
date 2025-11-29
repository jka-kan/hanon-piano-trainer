class Settings:
    def __init__(self):
        # Screen measures
        self.width = 1800
        self.height = 1000
        self.vert_line_color = "white"

        self.bpm = 0
        self.hands = ""

        # How many vertical lines in every beat.
        # This means the intended duration of the played note.
        # F. ex. if player wants to play 16th notes, the division is 4.
        # Line division must always match with the intended note duration.
        # Otherwise success/fail won't be calculated correctly.
        self.line_division = 4

        # How many metronome ticks are played in every beat.
        self.beat_division = 4

        # Only working: 5, 6, 9, 10
        self.beats_per_screen = 10
        self.wallclock = None
        self.perm_clock = None

        # Accuracy margin in ms.
        self.ms = 10
        self.accuracy_margin = self.ms / 1000  # ms to s
        self.metro_volume = 100
        self.vert_time_table = {}

        self.slot_time_table = {}


settings = Settings()
