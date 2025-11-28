################
# Just a simple editor to automatically create Hanon exercises.
#


import itertools

white_keys = {
    "A0": 21,
    "B0": 23,
    "C1": 24,
    "D1": 26,
    "E1": 28,
    "F1": 29,
    "G1": 31,
    "A1": 33,
    "B1": 35,
    "C2": 36,
    "D2": 38,
    "E2": 40,
    "F2": 41,
    "G2": 43,
    "A2": 45,
    "B2": 47,
    "C3": 48,
    "D3": 50,
    "E3": 52,
    "F3": 53,
    "G3": 55,
    "A3": 57,
    "B3": 59,
    "C4": 60,
    "D4": 62,
    "E4": 64,
    "F4": 65,
    "G4": 67,
    "A4": 69,
    "B4": 71,
    "C5": 72,
    "D5": 74,
    "E5": 76,
    "F5": 77,
    "G5": 79,
    "A5": 81,
    "B5": 83,
    "C6": 84,
    "D6": 86,
    "E6": 88,
    "F6": 89,
    "G6": 91,
    "A6": 93,
    "B6": 95,
    "C7": 96,
    "D7": 98,
    "E7": 100,
    "F7": 101,
    "G7": 103,
    "A7": 105,
    "B7": 107,
    "C8": 108,
}
import yaml

# 1
# pattern_up = ["C2", "E2", "F2", "G2", "A2", "G2", "F2", "E2"]
# pattern_down = ["G4", "E4", "D4", "C4", "B3", "C4", "D4", "E4"]

# 2
# pattern_up = ["C2", "E2", "A2", "G2", "F2", "G2", "F2", "E2"]
# pattern_down = ["G4", "D4", "B3", "C4", "D4", "C4", "D4", "E4"]
#
# finger_up_R = [1, 2, 5, 4, 3, 4, 3, 2]
# finger_down_R = [5, 2, 1, 2, 3, 2, 3, 4]
#
# finger_up_L = [5, 3, 1, 2, 3, 2, 3, 4]
# finger_down_L = [1, 3, 5, 4, 3, 4, 3, 2]

# 3
pattern_up = ["C2", "E2", "A2", "G2", "F2", "E2", "F2", "G2"]
pattern_down = ["G4", "D4", "B3", "C4", "D4", "E4", "D4", "C4"]

finger_up_R = [1, 2, 5, 4, 3, 2, 3, 4]
finger_down_R = [5, 2, 1, 2, 3, 4, 3, 2]

finger_up_L = [5, 3, 1, 2, 3, 4, 3, 2]
finger_down_L = [1, 3, 5, 4, 3, 2, 3, 4]


def make_sequence(pattern, hand, cycles, finger_pattern, direction):
    finger_iterator = itertools.cycle(finger_pattern)
    note_list = []
    new_key = ""
    duration = 16

    for cycle in range(cycles):

        for key in pattern:
            if hand == "R":
                orig_key = key[0] + str(int(key[1]) + 1)
            else:
                orig_key = key

            if direction == "up":
                keys_iterator = iter(white_keys.keys())
            else:
                keys_iterator = iter(reversed(white_keys.keys()))
            while True:

                new_key = next(keys_iterator)
                if orig_key == new_key:
                    for i in range(cycle):
                        new_key = next(keys_iterator)

                    print(new_key, end=" ")
                    item = (
                        new_key + "-" + str(duration) + "-" + str(next(finger_iterator))
                    )
                    note_list.append(item)
                    break
    print(note_list)
    return note_list


complete = {"R": [], "L": []}

# Left

complete["L"] = make_sequence(pattern_up, "L", 14, finger_up_L, "up")

for note in make_sequence(pattern_down, "L", 14, finger_down_L, "down"):
    complete["L"].append(note)

complete["L"].append("C2-16-5")


# Right

complete["R"] = make_sequence(pattern_up, "R", 14, finger_up_R, "up")

for note in make_sequence(pattern_down, "R", 14, finger_down_R, "down"):
    complete["R"].append(note)

complete["R"].append("C3-16-1")


print(complete)

with open("song.sng", "w") as f:
    yaml.dump(complete, f)
