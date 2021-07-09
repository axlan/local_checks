#!/usr/bin/env python3

# This script is based on http://www.richwhitehouse.com/index.php?postid=72
# which in turn was based on https://github.com/koalazak/dorita980 which is
# an actually decent node implementation

# While it can be used as a library function to query Roomba status,
# this script can also be used as a local check in check_mk
# https://docs.checkmk.com/latest/en/localchecks.html to make a server
# have a service monitoring a roomba. Outputs a string like:
# "P Roomba Battery=100;10:;5:|Wifi_RSSI=-66;-80:;-100: Roomba Status"

import socket, ssl
import time
import json
import os

import paho.mqtt.client as mqtt

from utils import get_recursively

ROOMBA_BROADCAST_PORT = 5678
ROOMBA_BROADCAST_MSG = "irobotmcs"
ROOMBA_BROADCAST_MAX_SIZE = 1024
ROOMBA_BROADCAST_TIMEOUT = 5.0

ROOMBA_PASS_PORT = 8883
ROOMBA_PASS_KEY = bytes((0xf0, 0x05, 0xef, 0xcc, 0x3b, 0x29, 0x00))
ROOMBA_PASS_MAX_SIZE = 1024

ROOMBA_TRACK_PORT = 8883
ROOMBA_TRACK_KEEPALIVE = 5

MQTT_TIMEOUT = 0.1
MQTT_MAXPACKETS = 16

# Function to report the presence of roombas on the network
# the status looks like:
# {'ver': '3', 'hostname': 'Roomba-ROOMBA_USER_NAME', 'robotname': 'Turkey', 'ip': '192.168.1.135', 'mac': '70:66:55:0A:DD:83', 'sw': '3.5.62', 'sku': 'R675020', 'nc': 0, 'proto': 'mqtt', 'cap': {'ota': 1, 'eco': 1, 'svcConf': 1}}
# Where ROOMBA_USER_NAME is the username needed to authenticate the MQTT
def broadcastFindRoomba():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(ROOMBA_BROADCAST_TIMEOUT)
    s.bind(("", ROOMBA_BROADCAST_PORT))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(ROOMBA_BROADCAST_MSG.encode("UTF-8"), ("255.255.255.255", ROOMBA_BROADCAST_PORT))
    foundAddr = {}
    startTime = time.time()
    while (time.time() - startTime) < ROOMBA_BROADCAST_TIMEOUT:
        try:
            data, addr = s.recvfrom(ROOMBA_BROADCAST_MAX_SIZE)
        except socket.timeout:
            continue
        if data and len(data) > 10:
            #being lazy about the validation here.
            try:
                tryParse = json.loads(data.decode("UTF-8"))
                #print("Received reply from Roomba:", tryParse, addr)
                foundAddr[tryParse["robotname"]] = tryParse
            except:
                pass
        time.sleep(0.1)
    s.close()
    return foundAddr

# Tries to get the password for a Roomba at IP addr
# You must do the following before running this function:
#   Make sure your robot is on the Home Base and powered on.
#   Then press and hold the HOME button on your robot until it plays a series of tones (about 2 seconds).
#   Release the button and your robot will flash WIFI light.
# returns a string with the password if successful
def getRoombaPassword(addr):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # Either of the following context settings worked for me - choose one
    # context.set_ciphers('HIGH:!DH:!aNULL')
    context.set_ciphers('DEFAULT@SECLEVEL=1')
    ssl_sock = context.wrap_socket(s)
    ssl_sock.connect((addr, ROOMBA_PASS_PORT))
    ssl_sock.send(ROOMBA_PASS_KEY)
    sliceFrom = 11
    data = bytearray()
    while True:
        data += ssl_sock.recv(ROOMBA_PASS_MAX_SIZE)
        if len(data) == 2:
            sliceFrom = 7
        elif len(data) >= 8:
            return data[sliceFrom:].decode("UTF-8")
        else:
            #print("Unexpected response length:", len(data))
            #print("Make sure you held down the HOME button")
            return None
    ssl_sock.close()
    return None

# MQTT Client for getting state from a Roomba
# In practice the Roomba usually only sends most of its status when first
# connected to, then mostly sends WiFi status
class RoombaClient:

    # Tries to connect with the supplied credentials
    def __init__(self, addr, username, password):
        self.state = {}
        try:
            mqttc = mqtt.Client(username)
            mqttc._userdata = self
            #mqttc.tls_set(ca_certs=CERT_PATH, certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1)
            # Errors on Ubuntu 20.04
            # See https://www.gitmemory.com/issue/keenlabs/KeenClient-Python/161/756683788
            # https://stackoverflow.com/questions/38015537/python-requests-exceptions-sslerror-dh-key-too-small
            #mqttc.tls_set(ca_certs=CERT_PATH, certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, ciphers='HIGH:!DH:!aNULL')
            mqttc.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, ciphers='HIGH:!DH:!aNULL')
            mqttc.username_pw_set(username, password)
            mqttc.on_message = self.__OnRoombaMessage
            mqttc.on_publish = self.__OnRoombaPublish
            mqttc.on_connect = self.__OnRoombaConnect
            mqttc.on_disconnected = self.__OnRoombaDisconnect
            mqttc.connect(addr, ROOMBA_TRACK_PORT, ROOMBA_TRACK_KEEPALIVE)
            self.mqttc = mqttc
        except Exception as e:
            # print(e)
            #print("Exception during MQTT connection. The device may not be accepting connections, or the socket may already be in use.")
            self.mqttc = None

    # Reports True if the connection succeeded
    def IsConnected(self):
        return self.mqttc is not None

    def __OnRoombaConnect(self, mqttc, userdata, flags, rc):
        #print('RoombaConnect')
        pass

    def __OnRoombaDisconnect(self, mqttc, userdata, rc):
        #print('RoombaDisconnect')
        pass

    def __OnRoombaMessage(self, mqttc, userdata, msg):
        #print(msg.topic)
        #print(msg.payload.decode("UTF-8"))
        data = json.loads(msg.payload.decode("UTF-8"))
        self.state.update(data['state']['reported'])

    def __OnRoombaPublish(self, mqttc, userdata, mid):
        #print('RoombaPublish')
        pass

    # Close connection
    def CloseExistingMqtt(self):
        if self.mqttc:
            self.mqttc.disconnect()
            self.mqttc = None
            return True
        return False

    """Return a dict of state info collected from MQTT messages
       returns all the state fields collected since connecting
       or the last time fresh==True was set.

    Keyword arguments:
    fields -- optional list of dict fields. The function will return
              immediately if the collected state has all the specified fields
    duration -- time to take before returning, or max duration to wait if fields are specified
    fresh -- clear the state previously received
    """
    def GetState(self, fields=None, duration=5.0, fresh=False):
        if self.mqttc:
            if fresh:
                self.state = {}
            start_time = time.time()
            while start_time + duration > time.time():
                r = self.mqttc.loop(MQTT_TIMEOUT, MQTT_MAXPACKETS)
                if r != 0:
                    #print("Lost connection to the Roomba.")
                    self.mqttc = None
                    break
                if fields:
                    found = [ len(get_recursively(self.state, field)) > 0 for field in fields ]
                    if all(found):
                        break
        return self.state
