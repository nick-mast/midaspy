## A script to write the current time to the MIDAS ODB
#N. Mast 2019
while true;
do
#echo "$(echo "odbedit -c 'set \"/Playground/time\"") "$(date +%s)""$(echo "'")"";
eval "$(echo "odbedit -c 'set \"/Playground/time\"") "$(date +%s)""$(echo "'")"";
sleep 1;
done
