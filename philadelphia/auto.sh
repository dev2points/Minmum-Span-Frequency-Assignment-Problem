TO=600

RESULTS_DIR=results/one_vertex
mkdir -p $RESULTS_DIR


runlim -r $TO python3 -u one_vertex.py P1 2>&1 | tee $RESULTS_DIR/P1.log
runlim -r $TO python3 -u one_vertex.py P2 2>&1 | tee $RESULTS_DIR/P2.log
runlim -r $TO python3 -u one_vertex.py P3 2>&1 | tee $RESULTS_DIR/P3.log
runlim -r $TO python3 -u one_vertex.py P4 2>&1 | tee $RESULTS_DIR/P4.log
runlim -r $TO python3 -u one_vertex.py P5 2>&1 | tee $RESULTS_DIR/P5.log
runlim -r $TO python3 -u one_vertex.py P6 2>&1 | tee $RESULTS_DIR/P6.log
runlim -r $TO python3 -u one_vertex.py P7 2>&1 | tee $RESULTS_DIR/P7.log
runlim -r $TO python3 -u one_vertex.py P8 2>&1 | tee $RESULTS_DIR/P8.log
runlim -r $TO python3 -u one_vertex.py P9 2>&1 | tee $RESULTS_DIR/P9.log
runlim -r $TO python3 -u one_vertex.py P10 2>&1 | tee $RESULTS_DIR/P10.log
runlim -r $TO python3 -u one_vertex.py P11 2>&1 | tee $RESULTS_DIR/P11.log
runlim -r $TO python3 -u one_vertex.py P12 2>&1 | tee $RESULTS_DIR/P12.log
runlim -r $TO python3 -u one_vertex.py P13 2>&1 | tee $RESULTS_DIR/P13.log
runlim -r $TO python3 -u one_vertex.py P14 2>&1 | tee $RESULTS_DIR/P14.log
runlim -r $TO python3 -u one_vertex.py P15 2>&1 | tee $RESULTS_DIR/P15.log
runlim -r $TO python3 -u one_vertex.py P16 2>&1 | tee $RESULTS_DIR/P16.log
runlim -r $TO python3 -u one_vertex.py P17 2>&1 | tee $RESULTS_DIR/P17.log
runlim -r $TO python3 -u one_vertex.py P18 2>&1 | tee $RESULTS_DIR/P18.log
runlim -r $TO python3 -u one_vertex.py P19 2>&1 | tee $RESULTS_DIR/P19.log
