# from pydoc import cli
import sys
import time
import threading
import pygame
from settings import settings
import note_api
import filemanager

# from pygame.mixer_music import play  # ← audio disabled
import pygame.midi

from settings import settings
from midi_routine import MidiRoutine

from pianoroll import PianoRollSprite
import pianoroll  # for first_round and barcontainer.init_bars()
import argparse


# -------------------- Pygame Init --------------------
# Testing computer audio metronome.
# pygame.mixer.pre_init(frequency=8000, size=-16, channels=1, buffer=128)  # ← audio disabled
# pygame.mixer.init()  # ← audio disabled


class App:
    def __init__(self) -> None:
        self.hands = ""
        self.filename = ""
        self.screen = None
        self.clock = None
        self.grid_group = None
        self.grid_a = None
        self.grid_b = None
        self.grid_order = []
        self.my_font = None
        self.midi_listen_thread = None
        self.metronome_thread = None
        self.song = None
        self.midi_routine = MidiRoutine()

    def init_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((settings.width, settings.height))
        pygame.display.set_caption("Hanon")
        self.clock = pygame.time.Clock()
        self.my_font = pygame.font.SysFont("Arial", 30)

    def load_song(self):
        self.song = note_api.process_song(
            filemanager.load_song(self.filename), self.hands
        )

    def init_midi(self):
        pygame.midi.init()
        self.midi_routine.midi_init()
        self.midi_routine.midi_init_out()

    def midi_stop(self):
        if self.midi_routine.metro_running.is_set():
            try:
                self.midi_routine.metro_running.clear()
                self.midi_listen_thread.join()
                self.metronome_thread.join()
                print(pygame.midi.get_init())
            except (AttributeError, UnboundLocalError):
                pass

    # -------------------- Sprites ------------------------
    def init_app(self, first=False):
        for grid in self.grid_order:
            grid.destroy()

        # Check: why does removing this double table init cause error?
        pianoroll.init_table()

        self.grid_group = pygame.sprite.Group()

        # First grid on-screen
        self.grid_a = PianoRollSprite(settings.height, settings.width, "A", 1)
        self.grid_a.rect.topleft = (0, 0)
        #    grid_a.precise_x = float(grid_a.rect.left)  # This can be used later to create smoother scroll

        # Second grid just off-screen to the right

        self.grid_b = PianoRollSprite(settings.height, settings.width, "B", 2)
        self.grid_b.rect.topleft = (settings.width, 0)  # +1
        #    grid_b.precise_x = float(grid_b.rect.left)

        self.grid_order = [self.grid_a, self.grid_b]
        self.grid_group.add(self.grid_a, self.grid_b)

        self.midi_routine.time_table = []

        self.midi_routine.metro_running.set()

        # Start MIDI input listener and metronome

        self.midi_listen_thread = threading.Thread(
            target=self.midi_routine.midi_listen
        )  # , daemon=True)
        self.midi_listen_thread.start()

        self.metronome_thread = threading.Thread(
            target=self.midi_routine.midi_tick
        )  # , daemon=True)
        self.metronome_thread.start()

    # -------------------- AUDIO CLICK REMOVED --------------------
    # click = pygame.mixer.Sound("metro.wav")
    # click_chan = pygame.mixer.Channel(0)

    # -------------------- MIDI → Visuals -----------------
    def handle_midi_messages(self, current_time: float):
        """Read MIDI queue and map to drawing on the rightmost grid."""

        while True:
            try:
                status, pitch, velocity = self.midi_routine.midi_queue.get_nowait()
            except queue.Empty:
                break

            # Pick the grid that is currently on the RIGHT (order == 1)
            target = self.grid_b if self.grid_b.order == 1 else grid_a

            # Draw position: distance from the right edge toward left
            draw_x = settings.width - target.rect.left
            for grid in (self.grid_a, self.grid_b):
                if grid.order == 1:
                    target.make_bar(draw_x, pitch - 21, status, current_time)

    # -------------------- Wrap when grid finished ---------------------
    def wrap_and_reseed_if_needed(self):
        """
        After sprites moved this frame:
        - Reset the right grid and replace the left grid with a fresh one on the right.
        """

        #     grid_order[1].reset_grid()

        new_grid = PianoRollSprite(settings.height, settings.width, "A", 2)
        new_grid.rect.x = settings.width

        # Copy notes that overlap to the next grid
        new_grid.copy_continuing_bars(self.grid_order[1])

        # Stop notes in the old grid
        # A note continuing from the old grid to the new is actually to notes connected
        self.grid_order[1].stop_continuing_bars()

        # Delete the left side grid and add new
        self.grid_order[0].kill()
        self.grid_order.pop(0)
        self.grid_order.append(new_grid)
        self.grid_group.add(new_grid)

        print("Grid changed!")

    # -------------------- Main ---------------------------
    def main(self):
        print("Starting MIDI listener.")
        print("Entering main loop.")
        running = True
        rounds = 0
        pixels_removed = 0

        # To be used later: adjust time gaps when starting new grid
        #    midi_zero = pygame.midi.time()

        # Measure pauses in playing. After a pause check whether played notes match with song notes.
        pause_start = None
        zero_time = 0

        if self.song:
            pianoroll.slots.make_comp_slots(self.song)

        while running:
            # Keep original timing relation for the grid logic
            # New pianoroll grid gets always the same time codes as previous ones
            # Time has to be adjusted to the midi time which is linear
            time_diff = pygame.midi.time() / 1000 - rounds

            # Time is compared to the grid time codes
            # Until the current midi time is found in the grid vertical points of the grid, pixels are removed
            # This is how line movement is perfectly synced with metronome ticks and midi in notes
            # Using clock caused out-of-sync
            pixels_removed, metro, grid_finished, cur_time = self.grid_order[
                0
            ].check_grid_table(time_diff)

            # print(
            #     "removed",
            #     pixels_removed,
            #     "metro",
            #     metro,
            #     "grid_finished",
            #     grid_finished,
            #     "cur_time",
            #     cur_time,
            # )

            # Test: controlling metronome ticks from main routine
            # This resulted uneven ticks

            # if metro:
            #     # Directly trigger a short MIDI tick (no audio, no events)
            #     midi_tick(received_time=time_diff)  # plays note_on, short gate, note_off

            # Update sprites (they should move using precise_x internally)
            self.grid_group.update(pixels_removed)

            # Read incoming midi notes and draw bars on the grid
            while not self.midi_routine.midi_queue.empty():

                message = self.midi_routine.midi_queue.get()
                channel = message[0][0]
                pitch = (
                    message[0][1] - 21
                )  # Adjust pitch because 0 isn't the lowest key in piano
                note_time = message[1] / 1000 - rounds

                self.grid_order[1].make_bar(channel, pitch, note_time)  # , line_time)
                pause_start = time.perf_counter()

            try:
                pause_time = time.perf_counter() - pause_start
                if pause_time >= 1 and self.song:
                    result = pianoroll.slots.check_slots()
                    if result:
                        filemanager.log_result(
                            self.filename, result, settings.bpm, self.hands
                        )

                    pause_start = None
            except TypeError:
                pass

            # Wrap if the grid is finished (out of the screen)
            if grid_finished:
                rounds += self.grid_order[0].time_per_screen
                self.wrap_and_reseed_if_needed()

            # --- Keyboard shortcuts ---
            keys = pygame.key.get_pressed()
            if keys[pygame.K_q]:
                running = False

            # --- Regular events (no METRO_EVENT consumption needed now) ---
            # Handling of key events is not currently working!
            # BPM and other variables cannot be changed on the fly
            # It is difficult to reset the program completely

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_KP_PLUS:
                        settings.bpm += 5
                        print("\nBPM: ", settings.bpm, "\n")
                        self.grid_order[1].initializing = True
                        self.midi_stop()
                        self.init_app()
                    elif event.key == pygame.K_KP_MINUS:
                        settings.bpm -= 5
                        print("\nBPM: ", settings.bpm, "\n")
                        self.init_app()
                        self.midi_stop()
                    elif event.key == pygame.K_KP_DIVIDE:
                        settings.line_division -= 1
                        print("\nLine division: ", settings.line_division, "\n")
                        self.init_app()
                    elif event.key == pygame.K_KP_MULTIPLY:
                        settings.line_division += 1
                        print("\nLine division: ", settings.line_division, "\n")
                        self.init_app()
                    elif event.key == pygame.K_INSERT:
                        settings.beat_division += 1
                        print("\nBeat division: ", settings.beat_division, "\n")
                        self.init_app()
                    elif event.key == pygame.K_PAUSE:
                        settings.beat_division -= 1
                        print("\nBeat division: ", settings.beat_division, "\n")
                        self.init_app()
                    elif event.key == pygame.K_PLUS:
                        settings.accuracy_margin += 2 / 1000
                        self.init_app()
                    elif event.key == pygame.K_MINUS:
                        settings.accuracy_margin -= 2 / 1000
                        print("Call")
                        self.init_app()

            # --- Text ---
            text = (
                "BPM: "
                + str(settings.bpm)
                + "  Line division: "
                + str(settings.line_division)
                + "  Beat division: "
                + str(settings.beat_division)
                + "  Accuracy (ms): "
                + str(round(settings.accuracy_margin * 1000))
            )

            text_surface = self.my_font.render(text, True, (255, 255, 255))

            self.screen.fill((0, 0, 0))
            self.grid_group.draw(self.screen)
            self.screen.blit(text_surface, (10, 10))

            pygame.display.flip()

            # --- Time step ---
            self.clock.tick(120)

        print("Exiting…")
        self.midi_stop()
        pygame.midi.quit()
        pygame.quit()
        sys.exit(0)


# Read variable arguments and start main routine
if __name__ == "__main__":
    app = App()
    app.init_midi()
    app.init_pygame()
    parser = argparse.ArgumentParser()
    parser.add_argument("bpm", type=int, help="BPM")
    parser.add_argument("hands", type=str, help="Hands")
    parser.add_argument("song", type=str, nargs="?", help="Song name")

    args = parser.parse_args()
    settings.bpm = args.bpm
    app.hands = args.hands
    app.init_app(first=True)

    if args.song:
        app.filename = args.song
        app.load_song()

    app.main()
