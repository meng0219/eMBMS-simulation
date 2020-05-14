import os

numUE = [225, 250, 275, 300]
for i in range(16):
    if i < 4:
        er = 0.0
    elif i < 8:
        er = 0.1
    elif i < 12:
        er = 0.3
    else:
        er = 0.6
    for j in range(20):
        print(er, numUE[i], ", times:", j+1)
        os.system("python main.py %i %f %i" % (numUE[i%4], er, i))