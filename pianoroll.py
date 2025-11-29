import pygame
import logging
from settings import settings
import queue
import copy
from midi_routine import metro_queue
from time import perf_counter
from collections import deque

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    style="%",
    datefmt="%Y-%m-%d %H:%M",
    force=True,
    level=logging.INFO,
)


to_transfer = {}
first_round = True

bars_continuing = queue.Queue()


def clear_continuing():
    global bars_continuing
    bars_continuing = queue.Queue()


class Slots:
    def __init__(self):
        self.slots = {}  # line_time: [slot nr, [pitches]]
        self.pointer = 0
        self.slots_all = {}  # slot: [pitches]
        self.computer_slots = {}
        self.computer_slots_test = {
            0: [19],
            1: [21],
            2: [23],
            3: [24],
            4: [26],
            5: [24],
            6: [23],
            7: [21],
            8: [19],
        }
        self.wait_to_next_grid = []

    def inc_pointer(self):
        self.pointer += 1

    def make_slot(self, line_time):
        self.slots[line_time] = [self.pointer, {}]
        logging.debug(
            "make_slot, self.slots: %s\n self.pointer: %s\n", self.slots, self.pointer
        )
        self.pointer += 1

    def finish_slots(self):
        logging.debug("finish_slots, self.slots: %s", self.slots)

        for line_time in self.slots:
            logging.debug("line_time: %s", line_time)
            try:
                self.slots_all[self.slots[line_time][0]] = self.slots[line_time][1]
            except IndexError:
                pass

        logging.debug(
            "at finish slots: self.slots_all: %s\nself.slots: %s",
            self.slots_all,
            self.slots,
        )

    def add_note(self, pitch, line_time, accurate, to_next_grid):

        # Check if note waiting for going to next grid
        if to_next_grid:
            self.wait_to_next_grid.append((pitch, line_time, accurate))
            return

        try:
            self.slots[line_time][1][pitch] = accurate
            if self.wait_to_next_grid:
                for elem in self.wait_to_next_grid:
                    new_pitch = elem[0]
                    new_line_time = 0.0
                    new_accurate = elem[2]
                    self.slots[new_line_time][1][new_pitch] = new_accurate
                self.wait_to_next_grid = []

        except KeyError:
            raise

    def make_comp_slots(self, song):
        for hand in song:
            for slot, pitch in enumerate(song[hand]):
                try:
                    self.computer_slots[slot].append(pitch[0] - 21)
                except KeyError:
                    self.computer_slots[slot] = [pitch[0] - 21]

    def check_slots(self):
        self.finish_slots()

        max_key_comp = max(self.computer_slots)
        max_key_user = max(self.slots_all)
        last_note_slot_user = -1
        amount_notes = 0
        amount_accurate = 0
        counter = 0
        notes_checked = 0

        for key in reversed(self.slots_all.keys()):
            print(key, self.slots_all[key])
            if self.slots_all[key]:
                last_note_slot_user = key
                break
        logging.info("Last key in user notes: %s", last_note_slot_user)

        if last_note_slot_user < 0:
            return

        for key in reversed(self.computer_slots.keys()):
            print(key, self.computer_slots[key])
            comp_notes = set(self.computer_slots[key])

            user_notes = self.slots_all[last_note_slot_user - counter]

            logging.info(
                "\nUSER notes in slot: %s\ndict key: %s\nComp notes in slot: %s",
                user_notes,
                last_note_slot_user - counter,
                comp_notes,
            )

            for pitch in user_notes:
                amount_notes += 1
                if user_notes[pitch]:
                    amount_accurate += 1
                    logging.info(
                        "SINGLE NOTE IN SLOT IS ACCURATE, amount accurates: %s",
                        amount_accurate,
                    )
            counter += 1

            user_notes = set(user_notes)

            if user_notes and comp_notes == user_notes:
                logging.info(
                    "ALL NOTES IN SLOT MATCH. comp_notes: %s\nuser_notes: %s\namount_accurate: %s",
                    comp_notes,
                    user_notes,
                    amount_accurate,
                )
            else:
                logging.info(
                    "Wrong notes played. Didn't match in slot. comp_notes %s\nuser_notes: %s\ncomp key: %s ",
                    comp_notes,
                    user_notes,
                    key,
                )
                #                self.slots = {}
                self.slots_all = {}

                return False
            notes_checked += 1

        logging.info("notes checked: %s", notes_checked)

        accuracy_rate = round(amount_accurate / amount_notes, 2)
        logging.info("\nALL MATCHED!! ACCURACY RATE: %s", accuracy_rate)

        for key in self.slots:
            self.slots[key] = []
        for key in self.slots_all:
            self.slots_all[key] = []
        # self.slots = {}
        # self.slots_all = {}
        return accuracy_rate


slots = Slots()


class BarContainer:
    """Container for Bar() instances."""

    def __init__(self):
        self.bars = {}
        self.make_empty_bars()

    def make_empty_bars(self):
        self.bars = {}
        for x in range(88):
            self.bars[x] = []


barcontainer = BarContainer()


class Table:
    """
    Contains tables for measuring time. These follow pygames midi clock.
    """

    def __init__(self) -> None:
        self.beats_per_screen = settings.beats_per_screen
        self.grid_table = []
        self.time_per_screen = 0.0
        self.one_grid_made = False
        # Time stamp : pixel number
        self.vert_time_table = {}

        # Time stamps for all vertical lines in grid starting from 0.0 secs
        self.all_vert_times = []

        # How many vertical lines in the grid
        self.amount_vert_lines = settings.line_division * self.beats_per_screen
        self.make_grid()

    def make_grid(self):
        """
        [ [pixel nr, time, metro True/False, line_time] ]
        """
        logging.debug("make_grid at Table")

        global slots

        self.grid_table = []
        beat_time = 60 / settings.bpm
        pixels_per_beat = settings.width / self.beats_per_screen

        self.time_per_screen = beat_time * self.beats_per_screen

        pixel_time = float(beat_time / pixels_per_beat)
        total_time = float(0.0)

        #        metro_pixel_interval = round((pixels_per_beat) / settings.beat_division)
        metro_pixel_interval = pixels_per_beat / settings.beat_division

        logging.debug(
            (
                "\nbeat time: %s pixels_per_beat: %s self.time_per_screen: %s"
                " pixel_time: %s self.amount_vert_lines: %s metro_pixel_interval: %s"
            ),
            beat_time,
            pixels_per_beat,
            self.time_per_screen,
            pixel_time,
            self.amount_vert_lines,
            metro_pixel_interval,
        )

        first_metro = True
        vert_line = False
        # Metronome intervals is a number of pixels between every tick
        # If the pixel number matches with this interval, put it in the list as a vertical line
        for pixel_nr in range(settings.width):
            if pixel_nr % metro_pixel_interval == 0 and not first_metro:
                # Points marked with metro will trigger metronome tick
                metro = True
            else:
                metro = False
                first_metro = False

            if pixel_nr % (pixels_per_beat / settings.line_division) == 0:
                self.vert_time_table[total_time] = pixel_nr
                self.all_vert_times.append(round(total_time, 4))
                vert_line = True
                # settings.slot_time_table[round(total_time, 4)] = [slots.pointer, []]
                # slots.inc_pointer += 1
                #                if not self.one_grid_made:
                slots.make_slot(round(total_time, 4))
                # logging.debug("total_time: %s", total_time)

            else:
                vert_line = False

            if pixel_nr % self.amount_vert_lines == 0:
                line_time = round(total_time, 4)
            else:
                line_time = -1

            self.grid_table.append(
                [pixel_nr, round(total_time, 4), metro, line_time, vert_line]
            )
            # self.grid_table.append([pixel_nr, total_time, metro, line_time, vertical line at this point])
            total_time += pixel_time

            # slots.finish_slots()

        logging.debug("total_time: %s", total_time)
        logging.debug("slot_time_table: %s", settings.slot_time_table)
        logging.debug("length vert %s", len(self.vert_time_table))
        logging.debug("\nvert_time_table: %s", self.vert_time_table)
        logging.debug("\nall_vert_times at make grid: %s", self.all_vert_times)
        #        logging.debug("\ngrid_table: %s", self.grid_table)
        logging.debug("\nslots: %s", slots.slots)

        # For the last comparison of accuracy
        self.all_vert_times.append(round(total_time, 4))

        if self.one_grid_made:
            self.one_grid_made = False
        else:
            self.one_grid_made = True
        settings.vert_time_table = copy.deepcopy(self.vert_time_table)
        return self.vert_time_table, self.all_vert_times, self.grid_table


# table = Table()


def init_table():
    # TODO: Put the tables in PianoRollSprite instance in stead of copying
    global table
    table = Table()
    settings.vert_time_table = table.vert_time_table


class Bar:
    """
    Note bar definitions.
    """

    def __init__(self, x, y, w, h, color, rect, pitch, playing, continuing):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.bar_rectangle = rect
        self.continuing = continuing
        self.playing = playing
        self.pitch = pitch
        self.copied_from_previous = False


class PianoRollSprite(pygame.sprite.Sprite):
    def __init__(self, height, width, name, order):
        super().__init__()

        self.name = name
        self.order = order
        self.screen_height = height
        self.screen_width = width
        self.clock = 0.0
        self.bars = {}
        self.vert_time_table = {}
        self.time_per_screen = 0.0
        self.screen_done = False
        self.initializing = False
        self.prev_line_time = -1
        self.next_line_time = -1

        self.notes_played = 0

        self.vert_lines = []
        self.vert_line = None
        self.all_vert_times = []

        # bar state (dynamic)
        self.bar_rect = None
        self.bar_color = pygame.Color("red")
        self.barcontainer = BarContainer()

        self.speed = 1
        self.line_division = settings.line_division  # 4
        self.beats_per_screen = settings.beats_per_screen
        self.beat_division = settings.beat_division  # 2

        self.amount_vert_lines = self.line_division * self.beats_per_screen
        self.vert_line_distance = round(
            settings.width / self.beats_per_screen / self.line_division
        )
        self.grid_table = []

        self.make_grid_table()

        # static grid surface
        self.grid_surface = pygame.Surface(
            (self.screen_width, self.screen_height), flags=pygame.SRCALPHA
        )
        self.image = self.grid_surface.copy()  # this is what the Sprite group blits
        self.rect = self.image.get_rect()

        # Height of the "piano key"
        self.horiz_distance = round(settings.height / 88)

        self.move_to_other_surface = {}
        self.received_bars = {}

        #        self.precise_x = float(self.rect.x)
        self.init_roller()

        # Draw static grid once on the pristine surface
        self._draw_horiz_lines(self.grid_surface)
        self._draw_vert_lines(self.grid_surface)

    def check_screen_done(self):
        # Is it time to switch to a new grid
        if self.rect.right <= 0:
            return True
        return False

    def make_grid_table(self):
        """
        [ [pixel nr, time, metro True, line_time] ]
        """
        global slots

        # ????
        slots.finish_slots()

        init_table()

        #        global table
        #        table = Table()
        self.grid_table = []
        beat_time = 60 / settings.bpm
        pixels_per_beat = settings.width / self.beats_per_screen
        self.time_per_screen = beat_time * self.beats_per_screen

        pixel_time = float(beat_time / pixels_per_beat)
        total_time = float(0.0)
        metro_pixel_interval = round((pixels_per_beat) / self.beat_division)

        self.vert_time_table = copy.deepcopy(table.vert_time_table)
        self.all_vert_times = copy.deepcopy(table.all_vert_times)
        self.grid_table = copy.deepcopy(table.grid_table)

        logging.debug(
            (
                "\nmetro_pixel_interval %s beat time: %s pixels_per_beat: %s"
                " self.time_per_screen: %s pixel_time: %s"
                " self.amount_vert_lines: %s"
            ),
            metro_pixel_interval,
            beat_time,
            pixels_per_beat,
            self.time_per_screen,
            pixel_time,
            self.amount_vert_lines,
        )

    def check_grid_table(self, clock):
        """
        Compares the grid lines to clock and removes x-positions that have been passed.
        Amount of pixels removed are used to update the screen scrolling.
        Signal if some of them had metronome marking.

        TODO: Because of the timing amount of removed pixels varies on every cycle.
        This creates uneven scrolling but secures sync with midi signals. Is there a way
        the make it smoother?
        """

        global slots
        metro = False
        pixels_removed = 0
        grid_finished = False

        # while True:
        try:
            while self.grid_table[0][1] <= clock:  # Was if
                # if self.grid_table[0][2]:
                #     metro = True
                #     metro_queue.put(True)

                if self.grid_table.pop(0)[4]:
                    logging.debug("clock: %s", clock)

                for elem in self.grid_table:
                    if elem[3] >= 0:
                        self.next_line_time = elem[3]
                        break

                pixels_removed += 1

            # if self.grid_table[0][1] > clock:
        #                break
        except IndexError:
            grid_finished = True

        if self.grid_table:
            cur_time = self.grid_table[0][1]
            # line_time = self.grid_table[0][3]
        else:
            cur_time = -1
            logging.debug("remove %s", pixels_removed)
        return (pixels_removed, metro, grid_finished, cur_time)  # , line_time)

    def _draw_horiz_lines(self, surf):
        y = 0
        for _ in range(88):
            pygame.draw.line(surf, "gray38", (0, y), (settings.width, y))
            y += self.horiz_distance

    def _draw_vert_lines(self, surf):
        global slots
        x = 0
        color = ""
        for i in range(self.amount_vert_lines - 1):

            #            self.all_vert_times.append(x)

            color = (
                "white"
                if (self.line_division and i % self.line_division == 0)
                else "gray38"
            )
            self.vert_lines.append(x + settings.width)
            pygame.draw.line(surf, color, (x, 0), (x, settings.height))
            x += self.vert_line_distance

        pygame.draw.line(surf, "green", (x, 0), (x, settings.height))
        self.vert_line = self.vert_lines.pop(0)

    def make_bar(self, channel, pitch, note_time):
        """Set bar position; actual drawing happens in update()."""
        top = self.calc_key_and_height(pitch)
        height = self.horiz_distance

        global bars_continuing
        global slots

        try:
            # Note ends
            if channel < 144:
                if self.barcontainer.bars[pitch]:
                    x = self.barcontainer.bars[pitch][-1].x
                    color = self.barcontainer.bars[pitch][-1].color
                    if self.barcontainer.bars[pitch][-1].copied_from_previous:
                        x = 0
                        width = settings.width - self.rect.x

                    else:
                        width = settings.width - self.rect.x - x
                    bar_rect = pygame.Rect(int(x), int(top), int(width), int(height))
                    bar = Bar(x, 0, width, height, color, bar_rect, pitch, False, False)

                    self.barcontainer.bars[pitch][-1] = bar

            # Make a new note
            # When a note is on, start drawing from the right border of the screen
            elif channel >= 144:
                self.notes_played += 1
                # print("notes_played: ", self.notes_played)
                x = settings.width - self.rect.left
                width = 40
                bar_rect = pygame.Rect(int(x), int(top), int(width), int(height))

                # print(
                #     "BAR NOTE TIME", note_time, self.prev_line_time, self.next_line_time
                # )

                # TODO: Unpack
                check_feedback = self.check_vert_times(note_time)

                if check_feedback[0]:
                    color = "green"
                else:
                    color = "brown"

                bar = Bar(x, 0, width, height, color, bar_rect, pitch, True, True)
                try:
                    self.barcontainer.bars[pitch].append(bar)
                except KeyError:
                    self.barcontainer.bars[pitch] = [bar]
                bars_continuing.put([bar])

                # pitch, accurate True, which slot (line_time)
                slots.add_note(
                    pitch,
                    check_feedback[1],
                    check_feedback[0],
                    check_feedback[2],
                )

        except KeyError:
            print("pitch", pitch)
            raise

    def calc_key_and_height(self, pitch):
        top = (
            settings.height
            - ((pitch) * self.horiz_distance)
            - (4 * self.horiz_distance)
        )
        height = self.horiz_distance
        return top

    def update_bars(self):
        """Update all note bars on the grid."""
        new_bars = {}
        global bars_continuing

        # Decide which bar are included when refreshing screen
        for pitch in self.barcontainer.bars:
            for bar in self.barcontainer.bars[pitch]:

                new_bar = bar
                if new_bar.playing and not new_bar.copied_from_previous:
                    new_bar.bar_rectangle.w = (
                        settings.width - self.rect.left - new_bar.bar_rectangle.left
                    )
                try:
                    new_bars[pitch].append(new_bar)
                except KeyError:
                    new_bars[pitch] = [new_bar]

        self.barcontainer.make_empty_bars()
        self.barcontainer.bars.update(new_bars)

    # Precise position calculation not currently in use
    def init_roller(self):
        self.precise_x = settings.width

    def set_bar_color(self, color):
        self.bar_color = pygame.Color(color)

    # This was a test for smoother scroll
    # def move(self, dt):
    #     target_distance = settings.width / self.beats_per_screen
    #     target_time = 1.0
    #     target_speed = target_distance / target_time
    #     #        self.rect.x -= self.speed
    #     self.precise_x -= target_speed * dt
    #     self.rect.x = round(self.precise_x)

    # example: flip color after moving (your logic can set_bar_color() instead)
    # self.set_bar_color("green")

    def reset_grid(self):
        self.make_grid_table()

    def stop_continuing_bars(self):
        """
        When a note continues over the grid border, stop it when changing grids.
        Then a new note is created on the new grid. These are in fact to note bars,
        but visually connected creating an impression of one continous note.
        """

        for pitch in self.barcontainer.bars:
            if self.barcontainer.bars[pitch]:
                self.barcontainer.bars[pitch][-1].playing = False
                if self.barcontainer.bars[pitch][-1].continuing:
                    old_bar = self.barcontainer.bars[pitch][-1]
                    x = old_bar.x
                    width = settings.width - self.rect.x - x

                    top = old_bar.bar_rectangle.top
                    height = old_bar.bar_rectangle.height

                    bar_rect = pygame.Rect(int(x), int(top), int(width), int(height))

                    # print(
                    #     "BAR NOTE TIME", note_time, self.prev_line_time, self.next_line_time
                    # )
                    #
                    color = old_bar.color

                    bar = Bar(x, 0, width, height, color, bar_rect, pitch, False, True)
                    try:
                        self.barcontainer.bars[pitch][-1] = bar
                    except KeyError:
                        raise
                        self.barcontainer.bars[pitch] = [bar]

    def copy_continuing_bars(self, other):
        # Notes continuing to the next grid are copied to a container when
        # new pianoroll instance is created.
        for pitch in other.barcontainer.bars:
            if other.barcontainer.bars[pitch]:
                new_bar = copy.deepcopy(other.barcontainer.bars[pitch][-1])
                if new_bar.continuing:

                    new_bar.bar_rectangle.x = 0  # settings.width - self.rect.left

                    new_bar.copied_from_previous = True
                    new_bar.playing = True
                    self.barcontainer.bars[pitch] = [new_bar]

    # print("\n\ncontainer", self.barcontainer.bars)

    def find_two_nearest_values(self, data_list, target_value):
        """
        Finds the two nearest values to a target_value in a given list.

        Args:
            data_list (list): The list of numbers to search within.
            target_value (float or int): The value to find the nearest elements to.

        Returns:
            list: A list containing the two nearest values from data_list.
                  Returns fewer than two values if data_list has less than two elements.
        """
        if len(data_list) < 2:
            return sorted(data_list, key=lambda x: abs(x - target_value))

        # Calculate absolute differences and store with original values
        differences = []
        for item in data_list:
            differences.append((abs(item - target_value), item))

        logging.debug("\ndifferences: %s", differences)
        # Sort by the absolute difference
        differences.sort()

        logging.debug("\ndifferences sort: %s ", differences)
        # Extract the two nearest values
        nearest_values = [differences[0][1], differences[1][1]]

        logging.debug("\nnearest values: %s", nearest_values)
        logging.debug("\nresult: %s", sorted([nearest_values[0], nearest_values[1]]))

        if max(nearest_values) == max(data_list):
            move_to_next = True
        else:
            move_to_next = False
        sorted_list = list(sorted(nearest_values))
        sorted_list.append(move_to_next)
        return sorted_list

    def check_vert_times(self, note_time):
        """
        Check whether played note was inside accuracy margin (success or fail).
        The note start time is compared to the nearest vertical line time stamp.
        The code assumes that the player tried to hit the nearest line.
        """
        # first_found = False
        # rect_x_to_border = settings.width - self.rect.x

        #        print("NOTE TIME AT CHECK: ", note_time)
        prev_line_time = 0.0
        next_line_time = 0.0
        removals = 0

        # Find nearest line

        # TODO: Put slice to match with divisions!!!

        prev_line_time, next_line_time, move_to_next = self.find_two_nearest_values(
            self.all_vert_times, note_time
        )

        # Was [0:41]

        logging.debug("all vert times %s ", self.all_vert_times)
        logging.debug(
            "prev line time: %s next line time: %s note time: %s",
            prev_line_time,
            next_line_time,
            note_time,
        )
        first_distance = round(note_time - prev_line_time, 4)

        second_distance = round(next_line_time - note_time, 4)
        distance = min([first_distance, second_distance])

        if first_distance >= second_distance:
            put_in = next_line_time
        else:
            put_in = prev_line_time

        # print("first:", first_distance, "second:", second_distance)
        # print(
        #     "note time: ",
        #     note_time,
        #     "prev line: ",
        #     prev_line_time,
        #     "next line: ",
        #     next_line_time,
        #     "\n dist first",
        #     first_distance,
        #     "second",
        #     second_distance,
        #     "distance",
        #     distance,
        # )

        if next_line_time == max(self.all_vert_times) and put_in == next_line_time:
            move_to_next = True
        else:
            move_to_next = False

        # Signal fail or success
        if distance > settings.accuracy_margin:
            return (False, put_in, move_to_next)
        return (True, put_in, move_to_next)

    def move(self, pixels):
        self.rect.x -= pixels

    def destroy(self):
        self.kill()

    def update(self, rate):
        # rebuild the sprite image from the pristine grid each frame
        self.image = self.grid_surface.copy()

        # draw dynamic elements (bar) on top
        self.update_bars()
        for pitch in self.barcontainer.bars:
            for bar in self.barcontainer.bars[pitch]:
                color = bar.color
                rect_obj = bar.bar_rectangle

                pygame.draw.rect(self.image, color, rect_obj, 0)
        self.move(rate)
