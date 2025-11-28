import yaml

new_list_L = []
new_list_R = []

old_list = []
with open("1.sng", "r") as f:
    for item in f:
        old_list = item.split()

finger_a = [1, 2, 3, 4, 5, 4, 3, 2]
finger_b = [5, 4, 3, 2, 1, 2, 3, 4]
from itertools import cycle

finger_cycle = cycle(finger_a)

for item in old_list:
    old_octave = int(item[1])
    new_octave = str(old_octave + 1)
    if "G4" in item:
        finger_cycle = cycle(finger_b)

    new_item_R = item[0] + new_octave + "-16-" + str(next(finger_cycle))
    #    new_item_L = item + "-16-" + str(next(finger_cycle))

    new_list_R.append(new_item_R)

new_list_R[-1] = "C3-16-2"

finger_cycle = cycle(finger_b)

for item in old_list:
    old_octave = int(item[1])
    new_octave = str(old_octave + 1)
    #    new_item_R = item[0] + new_octave + "-16-" + str(next(finger_cycle))
    if "G4" in item:
        finger_cycle = cycle(finger_a)
    new_item_L = item + "-16-" + str(next(finger_cycle))

    new_list_L.append(new_item_L)
    print(new_item_L)

new_list_L[-1] = "C2-16-4"


# with open("R-1.sng", "w") as f:
#  for item in new_list:
#    f.write((item + " "))

# with open("R-1.sng", "r") as f:
#     for item in f:
#         R.append(item)
#
print(new_list_L)
print(new_list_R)


notes = {"R": new_list_R, "L": new_list_L}

with open("final.sng", "w") as f:
    yaml.safe_dump(notes, f)
