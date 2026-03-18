TO=1200

RESULTS_DIR=results
mkdir -p $RESULTS_DIR


runlim -r $TO python3 -u main.py P1 2>&1 | tee $RESULTS_DIR/P1.log
runlim -r $TO python3 -u main.py P2 2>&1 | tee $RESULTS_DIR/P2.log
runlim -r $TO python3 -u main.py P3 2>&1 | tee $RESULTS_DIR/P3.log
runlim -r $TO python3 -u main.py P4 2>&1 | tee $RESULTS_DIR/P4.log
runlim -r $TO python3 -u main.py P5 2>&1 | tee $RESULTS_DIR/P5.log
runlim -r $TO python3 -u main.py P6 2>&1 | tee $RESULTS_DIR/P6.log
runlim -r $TO python3 -u main.py P7 2>&1 | tee $RESULTS_DIR/P7.log
runlim -r $TO python3 -u main.py P8 2>&1 | tee $RESULTS_DIR/P8.log
runlim -r $TO python3 -u main.py P9 2>&1 | tee $RESULTS_DIR/P9.log
runlim -r $TO python3 -u main.py P10 2>&1 | tee $RESULTS_DIR/P10.log
runlim -r $TO python3 -u main.py P11 2>&1 | tee $RESULTS_DIR/P11.log
runlim -r $TO python3 -u main.py P12 2>&1 | tee $RESULTS_DIR/P12.log
runlim -r $TO python3 -u main.py P13 2>&1 | tee $RESULTS_DIR/P13.log
runlim -r $TO python3 -u main.py P14 2>&1 | tee $RESULTS_DIR/P14.log
runlim -r $TO python3 -u main.py P15 2>&1 | tee $RESULTS_DIR/P15.log
runlim -r $TO python3 -u main.py P16 2>&1 | tee $RESULTS_DIR/P16.log
runlim -r $TO python3 -u main.py P17 2>&1 | tee $RESULTS_DIR/P17.log
runlim -r $TO python3 -u main.py P18 2>&1 | tee $RESULTS_DIR/P18.log
runlim -r $TO python3 -u main.py P19 2>&1 | tee $RESULTS_DIR/P19.log
