import json
import os
import glob
import socket
from datetime import time

from flask import Flask, request

from pytel import tg


#connecting to a TCP address
#after importing pytel, this function becomes useless
def traditional_tcp_connection():
    TCP_IP = '127.0.0.1'
    TCP_PORT = 443
    BUFFER_SIZE = 1024
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)

    conn, addr = s.accept()
    print('Connection address: {0}'.format(addr))
    while 1:
        data = conn.recv(BUFFER_SIZE)
        if not data: break
        print("received data: {0}".format(data))
        conn.send(data)  # echo
    conn.close()

class user_authentication:
    def __init__(self):
        self.users = []
        # TODO get json file with phone numbers and verification code from above
        self.new_user(phone_number="phone_number", vc="1234",
                      name="user", image="profile_img") #TODO load image

    def valid_user(self, users):
        last_user = users[0]
        current_index = 1
        while current_index < len(users):
            user = users[current_index]
            print('{0}'.format(last_user))
            print('{0}'.format(user))
            print("\n-----------\n")
            #check validity of nuber
            if user['phone_number'] != self.system(last_user[0]):
                #TODO check if this is correct
                return False

            last_user = user
            current_index += 1
        return True

    # def resolve_conflicts(self):
    #TODO think of this logic on my own

    def new_user(self, image, previous_user=None):
        individual_user = self.users
        name = individual_user[2]

        my_path = '/Users/staniya/Downloads/cybex_telegram_images'

        for file_names in os.listdir(os.getcwd()):
            infilename = os.path.join(my_path, file_names)
            if not os.path.isfile(infilename):
                continue
            base_file, ext = os.path.splitext(file_names)
            if ext == ".png" or ".gif" or ".bmp":
                os.rename(file_names, base_file + ".jpg")

        for images in glob.glob(os.path.join(my_path, '*.jpg')):
            image =



        user = {
            'index': len(self.users) + 1,
            'timestamp': time(),
            'name': name,
            'image': image,
            'previous_user': previous_user or self.users[-1]
        }

        #Reset the images
        self.image = []

        self.users.append(user)
        return user

    @staticmethod
    def system(user):
        user_string = json.dumps(user, sort_keys=True)
        return user_string

    @property
    def last_block(self):
        return self.users[-1]

app = Flask(__name__)

authentication = user_authentication()

@app.route('/users/new', methods = ['POST'])
def new_user():
    values = request.get_json()

    required = ['index', 'timestamp', 'name', 'image', 'previous_user']

    telegram = tg.Telegram('tcp://127.0.0.1:4444')