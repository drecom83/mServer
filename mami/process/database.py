from re import I
import re
import cherrypy
import os
import json
from mysql.connector import connect, Error
from mami import db_credentials_file


class DatabaseConnection():
    def __init__(self):
        self.credentials = None

    def get_connection(self):
        try:
            if not self.credentials or self.credentials == {}:
                self.credentials = self._get_credentials()
            return connect(
                host = self.credentials.get('host'),
                user = self.credentials.get('user'),
                password = self.credentials.get('password')
            )
        except Error as e:
            print(e)
        return None

    def _get_credentials(self, name="website"):
        try:
            with open(db_credentials_file) as f:
                read_credentials = f.read()
                all_credentials = json.loads(read_credentials)
                for items in all_credentials:
                    credentials = items.get(name)
                    if credentials:
                        return credentials
            return {}
        except Exception as inst:
            print(inst)
        return {}
        

class Database():
    '''
    singleton class
    '''
    '''
    _instance = None
    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.db_connection = DatabaseConnection()
            class_.connection = class_.db_connection.get_connection()
        return class_._instance
    '''

    def __init__(self):
        pass
        self.db_connection = DatabaseConnection()
        self.connection = self.db_connection.get_connection()

    def _get_result(self, db_query):
        '''
        remark: the with-statements does not seem to work
                there are issues with the context of it
                and is noted as a bug (somewhere)
        try:
            if not self.credentials or self.credentials == {}:
                self.credentials = self._get_credentials()
            with connect(
                host = self.credentials.get('host'),
                user = self.credentials.get('user'),
                password = self.credentials.get('password')
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(db_query)
                    result = cursor.fetchall()
                    return result
        except Error as e:
            print(e)
        '''
        try:
            cursor = self.connection.cursor()
            cursor.execute(db_query)
            result = cursor.fetchall()
            self.connection.close()  # remove this if it is a singleton
            return result
        except Exception as inst:
            print(inst, 'Check the credentials')
            return None

    def _update_db(self, db_query):
        try:
            cursor = self.connection.cursor()
            cursor.execute(db_query)
            result = cursor.fetchone()
            self.connection.commit()
            self.connection.close()
            return result
        except Exception as inst:
            print(inst, 'Check the credentials')
            return None

    def get_features_as_json(self):
        '''
        {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        4.497779,
                        52.053169
                    ]
                },
                "type": "Feature",
                "properties": {
                    "name": "De Hoop",
                    "mac_address": "84:CC:A8:A0:FE:2D"
                },
                "id": "nl_00937"
            }
        ]
        '''

        my_query = "SELECT \
                    mami_role.sender.id_sender, \
                    mami_role.sender.name, \
                    mami_role.sender.city, \
                    mami_role.sender.longitude, \
                    mami_role.sender.latitude, \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key;"
        
        result = self._get_result(my_query)
        features = '{ \
        "type": "FeatureCollection", \
        "features":['
        feature_items = ''
        for item in result:
            feature = '{ \
                    "geometry": { \
                    "type": "Point", \
                    "coordinates": [ \
                        %f, \
                        %f  \
                    ] \
                }, \
                "type": "Feature", \
                "properties": { \
                    "name": "%s", \
                    "city": "%s", \
                    "mac_address": "%s" \
                }, \
                "id": "%s" \
            },'

            feature_items += feature % (float(item[3]), float(item[4]), item[1], item[2], item[5], item[0])
        features += feature_items[:-1]  # remove last character (comma)
        features += ']}'
        return features

    def get_senders_as_json(self):
        '''
        {
            "A0:20:A6:29:18:13": {
                "comment": "de Roos",
                "key": "88888888-4444-4444-4444-121212121212",
                "previous_key": "88888888-4444-4444-4444-121212121212",
                "record_change_date": "",
                "ttl": "",
                "end_date": "",
                "proposed_key": "88888888-4444-4444-4444-121212121212"
            }
        },
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key;"

        result = self._get_result(my_query)
        senders = '['
        for item in result:
            sender = '{"%s" \
                :{ \
                "key":"%s", \
                "previous_key": "%s", \
                "record_change_date": "%s", \
                "ttl": "%s", \
                "end_date": "%s", \
                "proposed_key": "%s" \
                } \
                },'
            senders += sender % (item[0],
                                '88888888-4444-4444-4444-121212121212',
                                '88888888-4444-4444-4444-121212121212',
                                '',
                                '',
                                '',
                                '88888888-4444-4444-4444-121212121212')
        senders = senders[:-1]  # remove last character (comma)
        senders += ']'          
        return senders

    def get_models_as_json(self):
        '''
        {
            "84:CC:A8:B2:29:92": {
                "comment": "test motor",
                "key": "88888888-4444-4444-4444-121212121212",
                "previous_key": "88888888-4444-4444-4444-121212121212",
                "record_change_date": "",
                "ttl": "",
                "end_date": "",
                "proposed_key": "e5bace70-bbee-4c3c-84eb-cfcdcd177db5"
            }
        },
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.model \
                    WHERE mami_role.model.active = 1 \
                    AND mami_identification.authorisation.id = mami_role.model.authorisation_key;"

        result = self._get_result(my_query)
        models = '['
        for item in result:
            model = '{"%s" \
                :{ \
                "key":"%s", \
                "previous_key": "%s", \
                "record_change_date": "%s", \
                "ttl": "%s", \
                "end_date": "%s", \
                "proposed_key": "%s" \
                } \
                },'
            models += model % (item[0],
                                '88888888-4444-4444-4444-121212121212',
                                '88888888-4444-4444-4444-121212121212',
                                '',
                                '',
                                '',
                                '88888888-4444-4444-4444-121212121212')
        models = models[:-1]  # remove last character (comma)
        models += ']'          
        return models

    def validate_model(self, id):
        '''
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.model \
                    WHERE mami_role.model.active = 1 \
                    AND mami_identification.authorisation.authorisation_key = '%s' \
                    AND mami_identification.authorisation.id = mami_role.model.authorisation_key;" \
                    % id

        result = self._get_result(my_query)
        for item in result:
            if id in item:
                return True
        return False

    def validate_sender(self, id):
        '''
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.sender \
                    WHERE mami_role.sender.active = 1 \
                    AND mami_identification.authorisation.authorisation_key = '%s' \
                    AND mami_identification.authorisation.id = mami_role.sender.authorisation_key;" \
                    % id

        result = self._get_result(my_query)
        for item in result:
            if id in item:
                return True
        return False

    def validate_viewer(self, id):
        '''
        '''
        my_query = "SELECT \
                    mami_identification.authorisation.authorisation_key \
                    FROM mami_identification.authorisation, \
                        mami_role.viewer \
                    WHERE mami_role.viewer.active = 1 \
                    AND mami_identification.authorisation.authorisation_key = '%s' \
                    AND mami_identification.authorisation.id = mami_role.viewer.authorisation_key;" \
                    % id

        result = self._get_result(my_query)
        for item in result:
            if id in item:
                return True
        return False

    def write_sender_statistics(self, id=None, change_date='', revolutions=0):
        '''
        Get last record, calculate the new values and write the result back
        '''
        if id != None and int(revolutions) > 0:
            my_query = "SELECT `previous_count`, `latest_count`, `revolution_count` \
                        FROM `mami_statistic`.`sender` \
                        WHERE `id_sender` = '%s' \
                            AND date(`change_date`) >= '%s' AND date(`change_date`) <= '%s' \
                        ORDER BY `id` ASC LIMIT 1;" \
                        % (id, change_date, change_date)

            result = self._get_result(my_query)

            set_new_value_query = ''
            if len(result) == 0:
                # means a new day, previous_count stays null/None
                # current record is not a reliable daycounter value
                set_new_value_query = "INSERT \
                    INTO `mami_statistic`.`sender` \
                    (`id_sender`, `latest_count`, `revolution_count`) \
                    VALUES ('%s', '%d', '%d');" \
                    % (id, int(revolutions), int(revolutions))
            else:
                previous_count = result[0][0]
                latest_count = result[0][1]
                revolution_count = result[0][2]

                # if previous_count == None then it is the first entry of the day
                if previous_count == None:
                    previous_count = latest_count
                    revolution_count = 0
                else:
                    if int(revolutions) < previous_count:
                        # caused by a restart of the sender, internally counter = 0
                        revolution_count += int(revolutions)
                        latest_count = int(revolutions)

                    if int(revolutions) > previous_count:
                        # sender is internally accumulated
                        revolution_count += int(revolutions) - previous_count
                        latest_count = int(revolutions)

                previous_count = latest_count

                set_new_value_query = "UPDATE `mami_statistic`.`sender` \
                    SET `previous_count` = '%d', \
                        `latest_count` = '%d', \
                        `revolution_count` = '%d' \
                    WHERE `id_sender` = '%s' \
                        AND date(`change_date`) = '%s';" \
                    % (previous_count, latest_count, revolution_count, id, change_date)

            # have to make a new connection because self._get_result closed it
            self.db_connection = DatabaseConnection()
            self.connection = self.db_connection.get_connection()

            # write to database when new values have arrived
            if id != None and int(revolutions) > 0:
                result = self._update_db(set_new_value_query)


    def get_sender_statistics(self, id=None, from_date=None, last_date=None):
        '''
        Gets statistics from the sender table, including the dates mentioned
        If previous_count == null/None then the revolution_count is unreliable
        '''
        my_query = "SELECT `id`, `id_sender`, `change_date`, `revolution_count` \
                    FROM `mami_statistic`.`sender` \
                    WHERE `id_sender` = '%s' \
                        AND `previous_count` IS NOT NULL \
                        AND date(change_date) >= '%s' AND date(change_date) <= '%s' \
                    ORDER BY `change_date` ASC;" \
                    % (id, from_date, last_date)

        result = self._get_result(my_query)
        return result

