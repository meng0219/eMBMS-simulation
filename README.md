# eMBMS simulation
enhanced Multimedia Broadcast Multicast Services (eMBMS) is the broadcast mode of LTE. Using eMBMS, an eNodeB can efficiently broadcast the same data to all users attached to the cell. Furthermore, this simulation is based on Multimedia Broadcast multicast service Single Frequency Network (MBSFN) to implement eMBMS.
## Simulation scanerios
There is an LTE cell with no limit on the number of UEs.
Initially, there are some UE in the cell, and these UE will continuously move in the cell, but will not leave cell.
Furthermore, each UE has its priority for allocation resource and its needed data rate. 
If the UE's needed data rate cannot be satisfied by eNB, the data rate will be lower, i.e., adjusting QoE.
Additionally, the distribution of UEs is consistent with Pareto distribution.

During simulation, eNB will continuously, periodically and dynamically increases and reduces the resource of eMBMS and base on the resource amount to dynamically selects which real-time services will be transmitted by eMBMS.
** For detailed mechanisms, please refer to my master’s thesis https://link.springer.com/article/10.1007/s11235-021-00789-8**

The resource for eMBMS can occupy the total resource 0% to 60%. I would set it be 0%, 10%, 30% and 60% to simulate.
## Parameter
1. simulation duration: 2 h
2. number of RBs in a sub-frame: 15 RBs
3. maximum number of assigned RBs to a UE: 5 RBs
4. UE's movement speed: 60/70/80 km/h
5. number of service types: 4

see more paramater, please refere `simParams.py`
## Files
1. main.py: It contains main funcion to simulate whole experiment, and accepts three parameters to execute. Respectively, number of UEs, resource occupation rate of eMBMS and sheet index (for document the result on the xml file). And you can use the following command to execute the experiment.
```
python ./main.py 250 0.6 0
```
That's meaning there are 250 UE in the cell and eMBMS will occupy the 60% of resource to transmit service in maximum, and sheet index is 0.
2. simCls.py: It contains the class of UE and the class packet that is received from service provider.
3. simFunc.py: It contains all the used function.
4. simParams.py: It contains all the parameters for experiment except the number of UEs and the resource occupation rate of eMBMS.
5. run.py: It is not necessary in the experiment. It is used to automatically to run experiment in multiple times.
