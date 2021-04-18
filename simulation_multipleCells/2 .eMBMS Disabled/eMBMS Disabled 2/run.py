import os

ueInc = [1, 1, 3, 2]
IncSec = [2, 1, 2, 1]
sheet = 0
for i in range(len(ueInc)):
    for j in range(1):
        print(ueInc[i]/IncSec[i], 0.0, ", times:", j + 1)
        os.system(f"python main.py {ueInc[i]:d} {IncSec[i]:d} {0.0:f} {sheet:d}")
    sheet += 1
