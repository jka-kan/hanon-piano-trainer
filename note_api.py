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


def bak_process_song(song):
    note_list = song.split(" ")
    note_list.pop()
    print("NOTELIST", note_list)
    pitch_list = []
    for note in note_list:
        pitch_list.append(white_keys[note])
    print(pitch_list)
    return pitch_list


def process_song(song, hands):
    pitch_list = {"R": [], "L": []}
    if hands == "B":
        hands = ["R", "L"]
    for hand in hands:
        for note in song[hand]:
            pitch = white_keys[note[0:2]]
            duration = note[3:5]
            pitch_list[hand].append([pitch, int(duration)])
    print(pitch_list)
    return pitch_list
