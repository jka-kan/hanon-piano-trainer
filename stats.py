###############
#
# Simple tool for printing highest tempo and accuracy of exercises played by user.
#
###############

import yaml
import filemanager
import os


root_folder = "songs"
table = {}


def find_best_accuracy(sessions):
    max_acc = 0
    for session in sessions:
        if sessions[session] > max_acc:
            max_acc = sessions[session]
    return max_acc


def find_max_tempo(tempi):
    return max(list(tempi))


for root, dirs, files in os.walk(root_folder):
    for file in files:

        a = os.path.join(root, file)

        if file == "user.log":
            with open(a, "r") as f:
                data = yaml.safe_load(f)
                print(data)
                name = root[root.find("/") + 1 :]

                for hand in ["R", "L", "B"]:
                    if not data["results"][hand]:
                        table[name][hand] = None
                        continue
                    tempi = data["results"][hand].keys()
                    max_tempo = find_max_tempo(tempi)
                    max_acc = find_best_accuracy(data["results"][hand][max_tempo])

                    try:
                        table[name][hand] = (max_tempo, max_acc)
                    except KeyError:
                        table[name] = {hand: (max_tempo, max_acc)}

    print("\n\n", table, "\n\n")


keys = list(table.keys())
print(keys)
sorted_keys = []
for item in keys:
    name = int(item[item.find("/") + 1 :])
    sorted_keys.append(name)
sorted_keys.sort()
print(sorted_keys)

tempi = {}

from colorama import init as colorama_init
from colorama import Fore, Style

colorama_init()
txt_colors = [Fore.YELLOW, Fore.RESET]

print()
header = "".join("SONG".ljust(14))
header += "".join("RIGHT".ljust(25))
header += "".join("LEFT".ljust(25))
header += "".join("BOTH".ljust(10))
print(header)
print("-" * 90)

for song_nr in sorted_keys:
    line = "{color}"
    path = "hanon/" + str(song_nr)
    line += "".join(path.ljust(10))
    for hand in table[path]:
        try:
            bpm_line = str(table[path][hand][0])
            acc_line = str(round(table[path][hand][1] * 100))
        except TypeError:
            bpm_line = "--"
            acc_line = "--"

        line += hand + "  bpm: " + (bpm_line + "  acc: " + acc_line + " %    ")

    # line = (
    #     "{color}"
    #     + "".join(path.ljust(10))
    #     + "- max_bpm: "
    #     + str(table[path][0])
    #     + "  acc: "
    #     + str(round(table[path][1] * 100))
    #     + " %"
    # )

    txt = line.format(color=txt_colors[0])
    print(txt)
    txt_colors[0], txt_colors[1] = txt_colors[1], txt_colors[0]
