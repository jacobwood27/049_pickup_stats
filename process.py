import os.path
import fitdecode
from scipy import signal

import requests
import json
import io


def get_workouts(dat):

    with open('api.txt', 'r') as file:
        api_key = file.read()

    headers = {
        'Accept': 'application/json',
    }

    params = {
        'q': 'name contains \'Soccer\' and \'1SQyjNucZPj_T6XCr-XCCdBrqT81NO-Ht\' in parents',
        'key': api_key,
    }

    response = requests.get('https://www.googleapis.com/drive/v3/files', params=params, headers=headers)
    items = response.json()["files"]

    items = [item for item in items if not any(substring in item["name"][0:10] for substring in dat["name"])]

    for item in items:
        URL = "https://www.googleapis.com/drive/v3/files/" + item["id"] + "?alt=media&key=" + api_key
        response = requests.get(URL)
        open(item["name"], "wb").write(response.content)

    return items



def parse_workout(fname):

    TIMES  = []
    SPEEDS = []
    DIST   = []
    HR     = []

    with fitdecode.FitReader(fname) as fit:

        for frame in fit:
            # The yielded frame object is of one of the following types:
            # * fitdecode.FitHeader (FIT_FRAME_HEADER)
            # * fitdecode.FitDefinitionMessage (FIT_FRAME_DEFINITION)
            # * fitdecode.FitDataMessage (FIT_FRAME_DATA)
            # * fitdecode.FitCRC (FIT_FRAME_CRC)

            if frame.frame_type == fitdecode.FIT_FRAME_DATA:
                for f in frame.fields:
                    if f.name == "speed":
                        SPEEDS.append(f.value)
                    elif f.name == "timestamp":
                        TIMES.append(f.raw_value)
                    elif f.name == "distance":
                        DIST.append(f.value)
                    elif f.name == "heart_rate":
                        HR.append(f.value)

    dic = {
        "SPEEDS": SPEEDS,
        "TIMES": TIMES,
        "DIST": DIST,
        "HR": HR
        }

    return dic

def max2(list1):
    mx = max(list1[0], list1[1])
    secondmax = min(list1[0], list1[1])
    n = len(list1)
    for i in range(2,n):
        if list1[i] > mx:
            secondmax = mx
            mx = list1[i]
        elif list1[i] > secondmax and mx != list1[i]:
            secondmax = list1[i]
        elif mx == secondmax and secondmax != list1[i]:
            secondmax = list1[i]
    return secondmax

def get_cuts(speeds, THRESH=10.0/2.23):
    idx = [False for _ in speeds]
    cuts = []
    count = 0
    for i,s in enumerate(speeds):
        if s > THRESH:
            count += 1
            if count == 2:
                cuts.append([speeds[i-1],speeds[i]])
                idx[i-1] = True
                idx[i] = True
            elif count > 2:
                cuts[-1].append(s)
                idx[i] = True
        else:
            count = 0
    return cuts

def filter_speeds(v, fc = 0.1, fs = 1.0):
    w = fc / (fs / 2) # Normalize the frequency
    b, a = signal.butter(5, w, 'low')
    output = signal.filtfilt(b, a, v)
    return output

def get_stat(dat):
    vf = filter_speeds(dat["SPEEDS"])
    v  = dat["SPEEDS"]

    cutsf = get_cuts(vf)
    cuts = get_cuts(v)

    cutV = [max(sv) for sv in cutsf]
    cutL = [len(sv) for sv in cuts]

    n_cuts = len(cuts)
    L_cut_avg = sum(cutL)/n_cuts
    maxV = max([a for a in cutV if a < 22/2.237])
    avgV = sum(cutV)/len(cutV)

    ftr  = sum(i > (10.0/2.237) for i in v) / len(v)

    dist = dat["DIST"][-1]
    time = dat["TIMES"][-1] - dat["TIMES"][0]

    stat = {
        "TIME": time / 60,
        "DIST": dist / 1609,
        "MAXV": maxV * 2.237,
        "AVGV": avgV * 2.237,
        "AVGL": L_cut_avg,
        "NCUT": n_cuts,
        "FRAC": ftr,
    }

    print(stat)

    return stat

def write_stat(dat,stat,name):
    dat["name"].append(name[0:10])
    dat["time"].append(stat["TIME"])
    dat["dist"].append(stat["DIST"])
    dat["maxv"].append(stat["MAXV"])
    dat["avgv"].append(stat["AVGV"])
    dat["avgl"].append(stat["AVGL"])
    dat["ncut"].append(stat["NCUT"])
    dat["frac"].append(stat["FRAC"])

    with open('dat.json', 'w') as json_file:
        json.dump(dat, json_file)


def main():

    with open('dat.json', 'r') as f:
        dat = json.load(f)

    workouts = get_workouts(dat)

    for workout in workouts:
        data = parse_workout(workout["name"])
        stat = get_stat(data)
        write_stat(dat,stat,workout["name"])
        

if __name__ == '__main__':
    main()