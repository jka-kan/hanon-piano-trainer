# from pydoc import cli
import sys
import time
import queue
import threading
import pygame
from settings import settings

# from pygame.mixer_music import play  # ← audio disabled
import pygame.midi
from midi_routine import midi_queue


from settings import settings
from midi_routine import (
    METRO_EVENT,  # kept for compatibility, not used
    midi_listen,
    midi_init_out,
    midi_tick,
    midi_init,
    rounds,
    metro_running,
)
from pianoroll import PianoRollSprite
import pianoroll  # for first_round and barcontainer.init_bars()
import midi_routine

# from itertools import cycle
from time import perf_counter
import argparse


# -------------------- Pygame Init --------------------
# pygame.mixer.pre_init(frequency=8000, size=-16, channels=1, buffer=128)  # ← audio disabled
# pygame.mixer.init()  # ← audio disabled
pygame.init()


screen = pygame.display.set_mode((settings.width, settings.height))
pygame.display.set_caption("Hanon")

clock = pygame.time.Clock()

grid_group = None
grid_a = None
grid_b = None
grid_order = []

my_font = pygame.font.SysFont("Arial", 30)

midi_listen_thread = None
metronome_thread = None


def init_midi():
    pygame.midi.init()
    midi_init()
    midi_init_out()


def midi_stop():
    global midi_listen_thread
    global metronome_thread

    if metro_running.is_set():
        try:
            metro_running.clear()
            midi_listen_thread.join()
            metronome_thread.join()
            print(pygame.midi.get_init())

        except (AttributeError, UnboundLocalError):
            pass


# -------------------- Sprites ------------------------
def init_app(first=False):
    global grid_a
    global grid_b
    global grid_group
    global grid_order
    global midi_listen_thread
    global metronome_thread

    for grid in grid_order:
        grid.destroy()
    print(grid_group)

    pianoroll.init_table()

    grid_group = pygame.sprite.Group()

    # First grid on-screen
    grid_a = PianoRollSprite(settings.height, settings.width, "A", 1)
    grid_a.rect.topleft = (0, 0)
    #    grid_a.precise_x = float(grid_a.rect.left)  # This can be used later to create smoother scroll

    # Second grid just off-screen to the right
    grid_b = PianoRollSprite(settings.height, settings.width, "B", 2)
    grid_b.rect.topleft = (settings.width, 0)  # +1
    #    grid_b.precise_x = float(grid_b.rect.left)

    grid_order = [grid_a, grid_b]
    grid_group.add(grid_a, grid_b)

    midi_routine.time_table = []

    metro_running.set()

    # Start MIDI input listener and metronome

    midi_listen_thread = threading.Thread(target=midi_listen)  # , daemon=True)
    midi_listen_thread.start()

    metronome_thread = threading.Thread(target=midi_tick)  # , daemon=True)
    metronome_thread.start()


# -------------------- AUDIO CLICK REMOVED --------------------
# click = pygame.mixer.Sound("metro.wav")
# click_chan = pygame.mixer.Channel(0)


# -------------------- MIDI → Visuals -----------------
def handle_midi_messages(current_time: float):
    """Read MIDI queue and map to drawing on the rightmost grid."""
    global play_note_time
    global line_time

    while True:
        try:
            status, pitch, velocity = midi_queue.get_nowait()
        except queue.Empty:
            break

        # Pick the grid that is currently on the RIGHT (order == 1)
        target = grid_b if grid_b.order == 1 else grid_a

        # Draw position: distance from the right edge toward left
        draw_x = settings.width - target.rect.left
        for grid in (grid_a, grid_b):
            if grid.order == 1:
                target.make_bar(draw_x, pitch - 21, status, current_time)


# -------------------- Wrap when grid finished ---------------------
def wrap_and_reseed_if_needed():
    """
    After sprites moved this frame:
    - Reset the right grid and replace the left grid with a fresh one on the right.
    """

    global grid_a, grid_b, grid_order, grid_group

    grid_order[1].reset_grid()

    new_grid = PianoRollSprite(settings.height, settings.width, "A", 2)
    new_grid.rect.x = settings.width

    # Copy notes that overlap to the next grid
    new_grid.copy_continuing_bars(grid_order[1])

    # Stop notes in the old grid
    # A note continuing from the old grid to the new is actually to notes connected
    grid_order[1].stop_continuing_bars()

    # Delete the left side grid and add new
    grid_order[0].kill()
    grid_order.pop(0)
    grid_order.append(new_grid)
    grid_group.add(new_grid)


# -------------------- Main ---------------------------
def main():
    print("Starting MIDI listener.")
    print("Entering main loop.")

    running = True

    rounds = 0
    pixels_removed = 0

    # To be used later: adjust time gaps when starting new grid
    midi_zero = pygame.midi.time()

    while running:
        # Keep original timing relation for the grid logic
        # New pianoroll grid gets always the same time codes as previous ones
        # Time has to be adjusted to the midi time which is linear
        time_diff = pygame.midi.time() / 1000 - rounds

        #        print("time: ", time_diff)

        # Time is compared to the grid time codes
        # Until the current midi time is found in the grid vertical points of the grid, pixels are removed
        # This is how line movement is perfectly synced with metronome ticks and midi in notes
        # Using clock caused out-of-sync
        pixels_removed, metro, grid_finished, cur_time = grid_order[0].check_grid_table(
            time_diff
        )

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

        # Test: controlling of metronome ticks from main routine
        # This resulted uneven ticks

        # if metro:
        #     # Directly trigger a short MIDI tick (no audio, no events)
        #     midi_tick(received_time=time_diff)  # plays note_on, short gate, note_off

        # Update sprites (they should move using precise_x internally)
        grid_group.update(pixels_removed)

        # Read incoming midi notes and draw bars on the grid
        while not midi_queue.empty():
            message = midi_queue.get()
            channel = message[0][0]
            pitch = message[0][1] - 17
            note_time = message[1] / 1000 - rounds
            grid_order[1].make_bar(channel, pitch, note_time)  # , line_time)

        # Wrap if the grid is finished (out of the screen)
        if grid_finished:
            rounds += grid_order[0].time_per_screen
            wrap_and_reseed_if_needed()

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
                    grid_order[1].initializing = True
                    midi_stop()
                    init_app()
                elif event.key == pygame.K_KP_MINUS:
                    settings.bpm -= 5
                    print("\nBPM: ", settings.bpm, "\n")
                    init_app()
                    midi_stop()
                elif event.key == pygame.K_KP_DIVIDE:
                    settings.line_division -= 1
                    print("\nLine division: ", settings.line_division, "\n")
                    init_app()
                elif event.key == pygame.K_KP_MULTIPLY:
                    settings.line_division += 1
                    print("\nLine division: ", settings.line_division, "\n")
                    init_app()
                elif event.key == pygame.K_INSERT:
                    settings.beat_division += 1
                    print("\nBeat division: ", settings.beat_division, "\n")
                    init_app()
                elif event.key == pygame.K_PAUSE:
                    settings.beat_division -= 1
                    print("\nBeat division: ", settings.beat_division, "\n")
                    init_app()
                elif event.key == pygame.K_PLUS:
                    settings.accuracy_margin += 2 / 1000
                    init_app()
                elif event.key == pygame.K_MINUS:
                    settings.accuracy_margin -= 2 / 1000
                    print("Call")
                    init_app()

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

        text_surface = my_font.render(text, True, (255, 255, 255))

        screen.fill((0, 0, 0))
        grid_group.draw(screen)
        screen.blit(text_surface, (10, 10))

        pygame.display.flip()

        # --- Time step ---
        clock.tick(60)

    print("Exiting…")
    midi_stop()
    pygame.midi.quit()
    pygame.quit()
    sys.exit(0)


# Read variable arguments and start main routine
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("bpm", type=int, help="BPM", default=40)
    args = parser.parse_args()
    print(args.bpm)
    settings.bpm = args.bpm

    init_midi()
    init_app(first=True)

    main()
