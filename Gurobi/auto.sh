TO=600

RESULTS_DIR=results
mkdir -p $RESULTS_DIR


runlim -r $TO python3 -u gurobi.py P1 2>&1 | tee $RESULTS_DIR/P1.log
runlim -r $TO python3 -u gurobi.py P2 2>&1 | tee $RESULTS_DIR/P2.log
runlim -r $TO python3 -u gurobi.py P3 2>&1 | tee $RESULTS_DIR/P3.log
runlim -r $TO python3 -u gurobi.py P4 2>&1 | tee $RESULTS_DIR/P4.log
runlim -r $TO python3 -u gurobi.py P5 2>&1 | tee $RESULTS_DIR/P5.log
runlim -r $TO python3 -u gurobi.py P6 2>&1 | tee $RESULTS_DIR/P6.log
runlim -r $TO python3 -u gurobi.py P7 2>&1 | tee $RESULTS_DIR/P7.log
runlim -r $TO python3 -u gurobi.py P8 2>&1 | tee $RESULTS_DIR/P8.log
runlim -r $TO python3 -u gurobi.py P9 2>&1 | tee $RESULTS_DIR/P9.log
runlim -r $TO python3 -u gurobi.py P10 2>&1 | tee $RESULTS_DIR/P10.log
runlim -r $TO python3 -u gurobi.py P11 2>&1 | tee $RESULTS_DIR/P11.log

cd ..
cd CPLEX/CP
./auto.sh
cd ..
cd MIP
./auto.sh