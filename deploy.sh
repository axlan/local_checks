#!/usr/bin/env bash

DEPLOY_PATH=/usr/lib/check_mk_agent/local

sudo chmod 777 instances/*
sudo cp instances/roomba_check $DEPLOY_PATH/600
