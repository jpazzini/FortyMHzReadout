#!/bin/bash

# HELP SPARK TO INITIALIZE SENDING SMALL BATCHES AND WAITING FOR IT 
# TO PROCESS THEM BEFORE STARTING STREAMING 

./run_DMA_kafka_fullDMA -b "10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092" -t "test80" -c 1
sleep 10s

./run_DMA_kafka_fullDMA -b "10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092" -t "test80" -c 1 
sleep 8s

./run_DMA_kafka_fullDMA -b "10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092" -t "test80" -c 10
sleep 8s

./run_DMA_kafka_fullDMA -b "10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092" -t "test80" -c 100
sleep 8s

# START STREAMING
./run_DMA_kafka_fullDMA -b "10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092" -t "test80" -c -1
