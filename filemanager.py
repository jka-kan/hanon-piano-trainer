import yaml

filename = ""


def load_song(name):
    path = "songs/hanon/" + str(name) + "/"
    filename = path + str(name) + ".sng"
    with open(filename, "r") as f:
        data = yaml.safe_load(f)
    return data


def init_log():
    log = {
        "composer": "",
        "song": "",
        "min_duration": 16,
        "results": {"R": {}, "L": {}, "B": {}},
    }
    return log


def log_result(name, result, bpm, hands):
    log = {}
    path = "songs/hanon/" + str(name) + "/"

    filename = path + "user.log"

    try:
        with open(filename, "r") as f:
            log = yaml.safe_load(f)
    except FileNotFoundError:
        log = init_log()

    print(log)

    if bpm not in log["results"][hands]:
        log["results"][hands][bpm] = {}

    try:
        highest_session = max(log["results"][hands][bpm])
    except ValueError:
        highest_session = 0
    log["results"][hands][bpm][highest_session + 1] = result

    if name:
        with open(filename, "w") as f:
            yaml.dump(log, f)
    print_results(log, hands)
    return log


def print_results(log, hand):

    print("\nRESULTS:\n********\n")

    #    for hand in log["results"]:
    print("Hand: ", hand, "\n")
    for tempo in log["results"][hand]:
        print("bpm: ", tempo)
        all_results = []

        for session in log["results"][hand][tempo]:
            accuracy = log["results"][hand][tempo][session]
            print("      --- ", session, ":", accuracy)
            all_results.append(accuracy)
        print("Best result in tempo", tempo, ": ", max(all_results), "\n")
    print("------------------")
