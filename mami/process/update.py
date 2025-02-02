"""
Example of incomong headers
[HTTP_USER_AGENT] => ESP8266-http-Update
[HTTP_X_ESP8266_STA_MAC] => 18:FE:AA:AA:AA:AA
[HTTP_X_ESP8266_AP_MAC] => 1A:FE:AA:AA:AA:AA
[HTTP_X_ESP8266_FREE_SPACE] => 671744
[HTTP_X_ESP8266_SKETCH_SIZE] => 373940
[HTTP_X_ESP8266_SKETCH_MD5] => a56f8ef78a0bebd812f62067daf1408a
[HTTP_X_ESP8266_CHIP_SIZE] => 4194304
[HTTP_X_ESP8266_SDK_VERSION] => 1.3.0
[HTTP_X_ESP8266_VERSION] => DOOR-7-g14f53a19
"""


'''
Really coming in:
{'Remote-Addr': '10.0.0.53', 
'Host': '10.0.0.49:9090', 
'User-Agent': 'ESP8266-http-Update', 
'Connection': 'close', 
'X-Esp8266-Sta-Mac': 'A0:20:A6:14:85:06', 
'X-Esp8266-Ap-Mac': 'A2:20:A6:14:85:06', 
'X-Esp8266-Free-Space': '2740224', 
'X-Esp8266-Sketch-Size': '404368', 
'X-Esp8266-Sketch-Md5': '83d34178530e0738701d725292a1e1c3', 
'X-Esp8266-Chip-Size': '4194304', 
'X-Esp8266-Sdk-Version': '2.2.1(cfd48f3)', 
'X-Esp8266-Mode': 'sketch', 
'X-Esp8266-Version': '0.0001'}
'''

import os
import re
import hashlib
import cherrypy
import json
from mami import current_dir
from mami import firmware_dir
from mami import firmware_pattern
from mami.data.database import Database


class UpdateFirmware:
    @cherrypy.expose
    def default(self, *args, **kwargs):
        '''
        redirects all not-defined URLs to root.index
        '''
        # perform obsolete update for molen with version 0.1.2 or less
        # TODO: remove when all molen devices have a version of 0.1.3 or higher
        device = 'device' in kwargs.keys() and kwargs.get('device')
        version = 'version' in kwargs.keys() and kwargs.get('version')
        newUrl = '%s/updateFirmware/?device=%s&version=%s' % (cherrypy.request.script_name,
                                                              device,
                                                              version)
        raise cherrypy.HTTPRedirect(newUrl)


        #pass
        #newUrl = '%s%s' % (cherrypy.request.script_name, '/updateFirmware')
        #raise cherrypy.HTTPRedirect(newUrl)


    @cherrypy.expose
    def updateFirmware(self, device=None, version="latest"):
        """
        Update the latest firmware
        @param device: device can be 'model' or 'sender' or None(default = 'sender')
        or return a json formatted result
        """
        if device in ('sender', 'model'):
            result = {}
            update = Update(firmware_path=firmware_dir, firmware_pattern=firmware_pattern, device_function=device, requested_version=version)
            update_allowed, message_list = update.check_go()
            #print(update_allowed, message_list)
            if update_allowed:
                #print("geen update met bestand", update.filename)
                #return json.dumps({"nu": "niets"}).encode('utf-8', 'replace')
                return update.send_file()
            else:
                cherrypy.response.headers["Content-Type"] = "application/json"
                cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
                cherrypy.response.headers["Access-Control-Allow-Methods"] = "POST"
                cherrypy.response.headers["Cache-Control"] = "no-cache"
                cherrypy.response.headers["Connection"] = "keep-alive"
                cherrypy.response.headers["Pragma"] = "no-cache"
                result["Message"] = message_list
                return json.dumps(result).encode('utf-8', 'replace')
        else:
            return json.dumps({"Error": "Device unknown, should be sender or model"}).encode('utf-8', 'replace')


####################################################################################### 

class Update:
    def __init__(self, firmware_path='', firmware_pattern=r'*.', device_function=None, requested_version="latest"):
        '''
        @param device_function: is model or sender and corresponds with the filename
                                in db/authentication/sender|model
        '''
        self.firmware_path = os.path.join(current_dir, firmware_path, device_function)
        self.firmware_pattern = firmware_pattern
        self.device_function = device_function
        self.requested_version = requested_version
        self.device_user_agent = cherrypy.request.headers.get('User-Agent')
        self.device_firmware_version = cherrypy.request.headers.get('X-Esp8266-Version')
        self.device_station_mac_address = cherrypy.request.headers.get('X-Esp8266-Sta-Mac')
        if self.device_user_agent:
            user_agent_parts = self.device_user_agent.split('-')
            if requested_version == "latest":
                self.detected_firmware_version = '%s_%s.bin' % (user_agent_parts[0].lower(),
                                                                self.device_firmware_version)
            else:
                self.detected_firmware_version = '%s_%s.bin' % (user_agent_parts[0].lower(),
                                                                self.requested_version)

        self.firmware_file_list = self._get_ordered_filtered_firmware_list()
        self.filename = None

    def make_zero_filled_version(self, value):
        """
        Returns a left-side zero filled string for sorting
        e.g. value = 'esp8266_0.0.6.bin'
             firmware_pattern = r'^(.*?)_([0-9]+)\.([0-9]+)\.([0-9]+)\.bin'
             return: 00000000006
                     major(3 positions, max 2^8)
                     minor(3 positions, max 2^8)
                     patch(5 positions, max 2^16)
        """
        match = re.search(self.firmware_pattern, value)
        try:
            if match:
                # value = 'esp8266_0.0.6.bin'
                # firmware_pattern = r'^(.*?)_([0-9]+)\.([0-9]+)\.([0-9]+)\.bin'
                major = match.group(2).zfill(3)
                minor = match.group(3).zfill(3)
                patch = match.group(4).zfill(5)
                return '%s%s%s' % (major, minor, patch)
        except IndexError:
            pass
        return value

    def _get_ordered_filtered_firmware_list(self):
        """
        Returns an ordered, filtered list, using a regular expression
        using a callable method: self.make_zero_filled_version
        e.g. value = 'esp8266_0.0.6.bin'
             regular expression = r'^(.*?)_([0-9]+)\.([0-9]+)\.([0-9]+)\.bin'
        """
        firmware_list = [f for f in os.listdir(self.firmware_path) if re.match(self.firmware_pattern, f)]
        return sorted(firmware_list, key=self.make_zero_filled_version)

    def check_go(self):
        """
        Does all the checks and returns a True or False with a message
        The message consist of tuple with a HTTP status code and a text
        """
        ok = True
        message = []
        
        # check if there is a newer version
        if self.requested_version == "latest":
            if self._check_current_device_version_available() == True:
                if self._check_latest_update() == False:  # no action for update needed
                    ok = ok and False
                    message.append((200, 'You have the latest firmware, no further action needed'))  # 200 OK
                else:
                    # after checking, get the latest firmware
                    self.requested_firmware = self.firmware_file_list[-1]
                    self.filename = os.path.join(self.firmware_path, self.requested_firmware)
            else:
                try:
                    # just get the latest firmware
                    self.requested_firmware = self.firmware_file_list[-1]
                    self.filename = os.path.join(self.firmware_path, self.requested_firmware)
                except IndexError:
                    ok = ok and False
                    message.append((404, 'Cannot find requested firmware'))  # 404 Not Found
        else:
            # see check on "latest" in __init__(self)
            self.filename = os.path.join(self.firmware_path, self.detected_firmware_version)
        if self._check_file() == False:
            ok = ok and False
            message.append((404, 'Cannot find requested firmware'))  # 404 Not Found

        if self._mac_allow_update() == False:
            ok = ok and False
            message.append((403, 'MAC address is not authenticated to receive updates'))  # 403 Forbidden

        if self._check_user_agent() == False:
            ok = ok and False
            message.append((403, 'Unknown User Agent'))  # 403 Forbidden

        if self._check_headers() == False:
            ok = ok and False
            message.append((403, 'One or more Headers are invalid'))  # 403 Forbidden

        return ok, message

    def _check_file(self):
        """
        checks if the requested file exist and is available
        """
        return self.filename and os.path.exists(self.filename)

    def _check_latest_update(self):
        """
        Uses self.detected_firmware_version that gives the current firmware version
        self.firmware_file_list gives an ordered. filtered list of firmware that is
        known on the filesystem
        Check if the detected firmware is the last one in the list.
          if so, the detected version is also the latest

        Note: call this nethod only if self._check_current_device_version_available == True
        """
        try:
            if self.firmware_file_list.index(self.detected_firmware_version) + 1 == len(self.firmware_file_list):
                return False  # because no action for update is needed
            else:
                return True
        except ValueError as inst:
            #print(inst, ", check if the file is present")
            return False

    def _check_current_device_version_available(self):
        """
        Uses self.detected_firmware_version that gives the current firmware version
        self.firmware_file_list gives an ordered. filtered list of firmware that is
        known on the filesystem
        Check if the detected current firmware is present in the list.
        """
        try:
            if self.detected_firmware_version in self.firmware_file_list:
                return True
            else:
                return False
        except TypeError:
            return False


    def _check_header(self, header_name=None, header_value=None):
        if header_name not in cherrypy.request.headers:
            return False
        if header_value and cherrypy.request.headers[header_name.upper()] != header_value:
            return False
        return True

    def _check_user_agent(self):
        """
        Checks if the User Agent has the required (=expected) value
        """
        if not self._check_header('User-Agent', 'ESP8266-http-Update'):
            return False
        return True

    def _check_headers(self):
        """
        Checks the existense of given headers
        """
        if not self._check_header('X-Esp8266-Sta-Mac') \
        or not self._check_header('X-Esp8266-Ap-Mac') \
        or not self._check_header('X-Esp8266-Free-Space') \
        or not self._check_header('X-Esp8266-Sketch-Size') \
        or not self._check_header('X-Esp8266-Sketch-Md5') \
        or not self._check_header('X-Esp8266-Chip-Size') \
        or not self._check_header('X-Esp8266-Sdk-Version'):
            return False
        return True

    def _mac_allow_update(self):
        """ 
        Check to see if this request MAC address is allowed to be handled
        Use this method after check_headers()
        """
        try:
            database = Database()
            if self.device_function == 'model':
                return database.validate_model(cherrypy.request.headers['X-Esp8266-Sta-Mac'])
            if self.device_function == 'sender':
                return database.validate_sender(cherrypy.request.headers['X-Esp8266-Sta-Mac'])

            #for item in self.get_device_db():
            #    if item.get(cherrypy.request.headers['X-Esp8266-Sta-Mac']):
            #        return True
        except KeyError:
            pass
        return False

    def md5(self, filename=''):
        # Open,close, read file and calculate MD5 on its contents 
        with open(filename, mode='rb') as file_to_check:
            # read contents of the file
            data = file_to_check.read()    
            # pipe contents of the file through
            return hashlib.md5(data).hexdigest()

    def send_file(self):
        """
        Do checks and if they are all passed then send the file
        Otherwise give a usefull message or error
        """
        all_go, message = self.check_go()
        if all_go:
            cherrypy.response.headers["Content-Type"] = "application/octet-stream"
            cherrypy.response.headers["Content-Disposition"] = "attachment; filename=%s" % self.requested_firmware
            cherrypy.response.headers["Content-Length"] = os.path.getsize(self.filename)
            cherrypy.response.headers["X-Esp8266-Sketch-Md5"] = self.md5(self.filename)

            with open(self.filename, mode='rb') as file_handler:
                # read contents of the file
                file_content = file_handler.read()  # read whole file at once, should not give a memory problem
            return file_content
        else:
            print('Could not deliver firmware because', message)
            #first_message = message[0]
            #raise cherrypy.HTTPError(status=first_message[0], message=first_message[1])
            return
