#!/bin/bash
COUNTER=1
MAX_TRIES=100
echo "------- Executing command: 'python3 ${@}' -------"
until python3 $@ || ((COUNTER == MAX_TRIES))
do
    echo "Client lost connection. Retrying (${COUNTER}/$(($MAX_TRIES-1))) ..."
    ((COUNTER++))
    sleep 5
done
