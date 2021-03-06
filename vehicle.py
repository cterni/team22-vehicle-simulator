from threading import *
import requests
import time
import json

## status: ready, busy, oos
## vType: food
class Vehicle:
    def __init__(self, vehicleId, status, location, dock):
        self._vehicleId = vehicleId
        self._status = status
        self._location = location
        self._dock = dock
        self._heartbeating = False
        self._heartbeatThread = None
        self.routeRunning = False

    @property
    def vehicleId(self):
        return self._vehicleId

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    @property
    def dock(self):
        return self._dock

    @dock.setter
    def dock(self, value):
        self._dock = value

    @property
    def heartbeating(self):
        return self._heartbeating

    @heartbeating.setter
    def heartbeating(self, value):
        self._heartbeating = value

    def toDict(self):
        vAsDict = {}
        vAsDict["vehicleId"] = self.vehicleId
        vAsDict["location"] = self.location
        vAsDict["status"] = self.status
        return vAsDict
        
    def startHeartbeat(self):
        self.heartbeating = True
        if self._heartbeatThread == None or not self._heartbeatThread.is_alive():
            self._heartbeatThread = Thread(target=self.heartbeat, name=f"Vehicle_{self.vehicleId}")
            self._heartbeatThread.start()
        
    def endRoute(self):
        self.routeRunning = False

    def stopHeartBeat(self):
        self.heartbeating = False

    def heartbeat(self):
        while self.heartbeating:
            self.status = "ready"
            payload = self.toDict()
            try:
                heartbeatResponse = requests.put('https://supply.team22.sweispring21.tk/api/v1/supply/vehicleHeartbeat',  json=payload, timeout=10)
            except:
                continue
            ## handle responses - should either be something to denote that no order has been sent OR
            ## an array of locations / directions of route that should trigger the following Vehicle response
            ## ---->>> Change status to busy, startRoute() function

            if heartbeatResponse.status_code == 200:
                json_body = json.loads(heartbeatResponse.text)

                ## NO ROUTE to equal no order / do nothing yet response
                if json_body == {'Heartbeat' : 'Received'}:
                    if self.location != self.dock:

                        # Gen Route from location to dock
                        # New API post call to recive route from dispatch / mapbox

                        self.status = 'busy'
                        payload = self.toDict()
                        try:
                            heartbeatResponse = requests.put('https://supply.team22.sweispring21.tk/api/v1/supply/vehicleHeartbeat',  json=payload, timeout=10)
                        except:
                            continue
                        time.sleep(20)
                        self.location = self.dock

                else:
                    self.startRoute(json_body)
                    ## consider sending a different HTTP Request as order confirmation
            else:
                print(f"Heartbeat failed:  {heartbeatResponse.status_code} for vehicle: {self.vehicleId}" )

            time.sleep(15)

        self.status = 'oos'
        payload = self.toDict()
        try:
            heartbeatResponse = requests.put('https://supply.team22.sweispring21.tk/api/v1/supply/vehicleHeartbeat',  json=payload, timeout=10)
        except:
            pass
        

    def toString(self):
        retStr = f"""ID = {self.vehicleId} *** STATUS = {self.status} *** LOCATION = {self.location} *** DOCK = {self.dock} *** isHB = {self.heartbeating} ***"""
        return retStr

    def startRoute(self, route):
        self.status = 'busy'
        self.routeRunning = True

        duration = route["duration"]

        coordinates = route["coordinates"]
        ## STORE ROUTE RESPONSE TO ARRAY FOR VEHICLE USE

        ## Create step interval / time (Realistic ETA)
        timePerStep = duration / float(len(coordinates))

        last_index_location = 0
        last_location_latitude = float(self.location.split(",")[0])
        last_location_longitude = float(self.location.split(",")[1])

        for i in range(0, len(coordinates)):
            coordinate = coordinates[i]
            latitude = coordinate[0]
            longitude = coordinate[1]
            if last_location_latitude == latitude and last_location_longitude == longitude:
                last_index_location = i
                break

        ## finalDest and reverse nextStep() until dock
        ## once at dock, update status to ready
        while self.routeRunning and last_index_location < len(coordinates):
            coordinate = coordinates[last_index_location]
            latitude = coordinate[0]
            longitude = coordinate[1]
            self.location = f"{latitude},{longitude}"

            if self.heartbeating:
                payload = self.toDict()
                try:
                    heartbeatResponse = requests.put('https://supply.team22.sweispring21.tk/api/v1/supply/vehicleHeartbeat',  json=payload, timeout=10)
                except:
                    continue
            time.sleep(timePerStep)
            last_index_location += 1

        # Hearbeat off, completed route: WAIT FOR UPDATE
        if not self._heartbeating and self.routeRunning:
            while not self.heartbeating and self.routeRunning:
                time.sleep(5)
            payload = self.toDict()

            # If request fails to notify, try again
            passed = False
            while not passed:
                try:
                    heartbeatResponse = requests.put('https://supply.team22.sweispring21.tk/api/v1/supply/vehicleHeartbeat',  json=payload, timeout=10)
                    if (heartbeatResponse.status_code == 200):
                        passed = True
                except:
                    pass

        ## Return to Dock
        last_index_location = len(coordinates) - 1
        while self.routeRunning and last_index_location >= 0:
            coordinate = coordinates[last_index_location]
            latitude = coordinate[0]
            longitude = coordinate[1]
            self.location = f"{latitude},{longitude}"

            if self.heartbeating:
                payload = self.toDict()
                try:
                    heartbeatResponse = requests.put('https://supply.team22.sweispring21.tk/api/v1/supply/vehicleHeartbeat',  json=payload, timeout=10)
                except:
                    pass
            time.sleep(timePerStep)
            last_index_location -= 1

        if self.heartbeating:
            self.location = self.dock
            self.status = 'ready'

        self.routeRunning = False

    def __eq__(self, value):
        return isinstance(value, Vehicle) and self.vehicleId == value.vehicleId

    def __hash__(self):
        return hash(self.vehicleId)
## TESTING
def main():
    pass

if __name__ == "__main__":
    main()