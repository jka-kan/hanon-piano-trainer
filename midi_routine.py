from sys import exception
import time

# import rtmidi
import logging
import queue
import pygame
import pygame.midi
from settings import settings
import threading


logging.basicConfig(level=logging.INFO)

# METRO_EVENT = pygame.USEREVENT + 1  # kept for compatibility with your imports


class MidiRoutine:
    def __init__(self) -> None:
        self.device_id_input = 5  # Change DEVICE IN number if needed
        self.device_id_output = 4  # Change DEVICE OUT
        self.midi_in = None
        self.output = None
        self.midi_queue = queue.Queue()
        self.rounds = 0
        self.first_round = True
        self.time_table = []
        self.metro_running = threading.Event()
        self.prev_time = 0.0
        self.midi_queue = queue.Queue()

    def midi_init(self):
        for dev in range(pygame.midi.get_count()):
            print(pygame.midi.get_device_info(dev))

        device_id = pygame.midi.get_default_input_id()
        print("dev", device_id, pygame.midi.get_device_info(5))
        if device_id == -1:
            logging.warning("No MIDI input device found.")
            self.midi_in = None
            return

        try:
            self.midi_in = pygame.midi.Input(self.device_id_input)
        except Exception as e:
            logging.error(f"Failed to open MIDI input (id={self.device_id_input}): {e}")
            self.midi_in = None

    def midi_init_out(self):
        # Find an output device (replace with your specific device ID if needed)
        output_device_id = pygame.midi.get_default_output_id()
        if output_device_id == -1:
            print("No MIDI output device found.")
        try:
            self.output = pygame.midi.Output(self.device_id_output)
        except Exception as e:
            logging.error(f"Failed to open MIDI output (id=4): {e}")
            self.output = None

    # Adjustement not in use
    def midi_time_adjusted(self, midi_zero):
        return pygame.midi.time()  #  + midi_zero

    def midi_send(self, message):
        """
        Kept for reference. No longer used for metronome tick.
        Previously tried to read pygame events from a thread, which is unsafe.
        """
        channel = message[0][0]
        pitch = message[0][1]
        velocity = 50

        if channel >= 144:
            self.output.note_on(64, velocity)
        else:
            self.output.note_off(64, velocity)

        # for event in pygame.event.get(eventtype=METRO_EVENT):
        #     output.note_on(81 + 27, 30, 0)
        #     output.note_off(81 + 27, 30, 0)
        return

    def midi_tick(
        self,
        note=81 + 27,
        velocity=30,
        channel=0,
        gate_seconds=0.003,
        received_time=0.0,
    ):
        """
        A 'fake' metronome. The piano plays a hihat drum sound on General Midi sound bank.
        If your piano has different patch channels you have to change to match with your
        piano specifications.
        If your piano doesn't support GM patches, you can use an ordinary note instead.
        For example the highest note in the piano.
        Metronome sound is played when midi time matches with pixels in the time table.
        The midi clock can't be reset, it runs continously. Thats why the time table
        must be corrected with elapsed time when new grid starts.
        """

        # Send a short MIDI click (Note On + small gate + Note Off).
        # Called directly when 'metro' is True from the grid.

        midi_zero = 0  # pygame.midi.time()

        channel = 9
        note = 42
        if self.output is None:
            return
        adjusted = 0

        while self.metro_running.is_set():
            if not self.time_table:
                # Make time table for metronome ticks.
                # To continue from a grid to another start with the last tick of the
                # previous grid (=adjustement).
                # First tick of the next grid is one step + adjustement

                a = list(settings.vert_time_table.keys())[0]
                b = list(settings.vert_time_table.keys())[1]
                step = (b - a) * 1000

                for key in settings.vert_time_table:
                    self.time_table.append((key * 1000) + adjusted)
                self.rounds += 1
                adjusted = self.time_table[-1] + step

            # print(
            #     "\ntime table: ",
            #     self.time_table,
            #     " length: ",
            #     len(self.time_table),
            #     "midi time: ",
            #     pygame.midi.time(),
            #     "\n",
            # )

            midi_now = pygame.midi.time()
            # print("at midi time: ", midi_now)
            if midi_now >= self.time_table[0]:
                try:
                    # print(
                    #     "METRO out time: ",
                    #     pygame.midi.time() / 1000,
                    #     "received time: ",
                    #     received_time,
                    #     "diff: ",
                    #     diff,
                    # )
                    #

                    self.output.note_on(note, settings.metro_volume, channel)
                    # time.sleep(0.001)
                    self.output.note_off(note, settings.metro_volume, channel)
                except Exception as e:
                    logging.error(f"MIDI tick failed: {e}")
                self.time_table.pop(0)
            else:
                time.sleep(0.002)

        # This was a test for receiving metronome signals from elsewhere. Didn't sync well.
        ###################################################################################
        # def midi_tick(
        #     note=81 + 27, velocity=30, channel=0, gate_seconds=0.03, received_time=0.0
        # ):
        #     """
        #     Send a short MIDI click (Note On + small gate + Note Off).
        #     Called directly when 'metro' is True from the grid.
        #     """
        #     global output
        #     channel = 9
        #     note = 42
        #     global prev_time
        #     if output is None:
        #         return
        #     try:
        #         diff = round(received_time - prev_time, 4)
        #         prev_time = received_time
        #         # print(
        #         #     "METRO out time: ",
        #         #     pygame.midi.time() / 1000,
        #         #     "received time: ",
        #         #     received_time,
        #         #     "diff: ",
        #         #     diff,
        #         # )
        #         output.note_on(note, settings.metro_volume, channel)
        #         time.sleep(gate_seconds)
        #         output.note_off(note, settings.metro_volume, channel)
        #     except Exception as e:
        #         logging.error(f"MIDI tick failed: {e}")
        ###################################################################################

    def midi_listen(self):

        if self.midi_in is None:
            # Optional: rtmidi fallback if pygame.midi input is not opened
            try:
                midi_in_rt = rtmidi.MidiIn()
                available_ports = midi_in_rt.get_ports()
                if not available_ports:
                    print("No MIDI input devices found.")
                    return
                try:
                    port_to_open = 0
                    print(f"\nOpening port: '{available_ports[port_to_open]}'")
                    midi_in_rt.open_port(port_to_open)
                except (
                    rtmidi.InvalidPortError,
                    rtmidi.NoDevicesError,
                    IndexError,
                ) as e:
                    print(f"Error opening port: {e}")
                    return

                print("MIDI Thread is now listening (rtmidi)…")
                while True:
                    message = midi_in_rt.get_message()
                    if message:
                        midi_data, deltatime = message
                        print("delta at midi:", deltatime, "abs. time: ", time.time())
                    time.sleep(0.001)
            except Exception as e:
                print(f"No MIDI input active: {e}")
                return
        else:
            print("MIDI Thread is now listening (pygame.midi).")
            while self.metro_running.is_set():  # True:
                try:
                    if self.midi_in.poll():
                        midi_events = self.midi_in.read(5)
                        for midi_event in midi_events:
                            self.midi_queue.put(midi_event)
                            #              print(f"MIDI Event: {midi_event}")

                            # status = midi_event[0][0]
                            # if 0x90 <= status <= 0x9F:
                            #     note = midi_event[0][1]
                            #     velocity = midi_event[0][2]
                            #     # print(
                            #     #     "\nMIDI IN time: ",
                            #     #     midi_event[1] / 1000,
                            #     #     "interval: ",
                            #     #     midi_event[1] - prev_note_time,
                            #     #     "\n",
                            #     # )
                            #     # prev_note_time = midi_event[1]
                            # #                  print(f"Note On: Note={note}, Velocity={velocity}")
                            # elif 0x80 <= status <= 0x8F:
                            #     note = midi_event[0][1]

                    else:
                        time.sleep(0.005)
                except Exception as e:
                    logging.error(f"MIDI listen error: {e}")
                    time.sleep(0.1)
