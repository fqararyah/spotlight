conda activate spotlight-ae
./run-ae.sh single --model RESNET --target EDP --technique Spotlight --scale Edge
./run-ae.sh single --model VGG16 --target EDP --technique Spotlight --scale Edge
#./run-ae.sh single --model TRANSFORMER --target EDP --technique Spotlight --scale Edge