#!/usr/bin/env bash

DEPLOY_PATH=/usr/lib/check_mk_agent/local

sudo chmod 777 instances/*

sudo cp utils.py $DEPLOY_PATH/scripts/

sudo cp roomba.py $DEPLOY_PATH/scripts/
sudo cp roomba_check $DEPLOY_PATH/scripts/
sudo cp instances/roomba_check $DEPLOY_PATH/600/

sudo cp reolink_check $DEPLOY_PATH/scripts/
sudo cp instances/reolink_patio_check $DEPLOY_PATH/600/
sudo cp instances/reolink_kitchen_check $DEPLOY_PATH/600/
