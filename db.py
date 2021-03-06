
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from pymemcache.client import base
from coordinates import Coordinate
from time import sleep
import utils
from shapely.geometry import Point
Coordinate.default_order = 'yx'
import threading


class DB:
    # Use the application default credentials
    def __init__(self):
        firebase_admin.initialize_app()
        self.db = firestore.client()
        self.status = self.db.collection(u'status')
        self.conf = self.db.collection(u'conf')
        self.mission = self.db.collection(u'mission')
        self.client = base.Client(('localhost', 11211))

    def get_key_float(self,key):
        valor=None
        try:
            valor=float(self.client.get(key))
        except Exception as e:
            valor=-2
            print('KeyErr',key, repr(e))
        return valor

    def update(self):
        data={
            u'lat': (self.get_key_float('lat')),
            u'lon': (self.get_key_float('lon')),
            u'sat': (self.get_key_float('sat')),
            u'age': (self.get_key_float('age')),
            u'spd': (self.get_key_float('spd')),
            u'nav': (self.get_key_float('nav')),
            u'modo': self.client.get('mode').decode("utf-8") ,
            u'timestamp': firestore.SERVER_TIMESTAMP,
            u'actual': int(self.get_key_float('steersensor')),
        }
        self.status.document("data").update(data)

    def update_child(self):
        while True:
            try:
                sleep(2)
                self.update()
            except Exception as e:
                print("UPLOAD Error",repr(e))

    def run(self):
        t1 = threading.Thread(target=self.update_child)
        t1.start()
        def update_modo( doc_snapshot, changes, read_time):
            try:
                modo=doc_snapshot[0].to_dict()["mode"]
                print(modo)
                self.client.set('mode',modo)
            except Exception as e:
                print("Error actualizar modo", repr(e))

        def update_conf( doc_snapshot, changes, read_time):
            try:
                params=doc_snapshot[0].to_dict()
                self.client.set('p', params["p"])
                self.client.set('i', params["i"])
                self.client.set('d', params["d"])
                self.client.set('ancho',params["ancho"])
                self.client.set('centro',params["centro"])
            except Exception as e:
                print("Error actualizar conf", repr(e))
        self.mode_watch = self.status.document("nav").on_snapshot(update_modo)
        self.mode_watch2 = self.conf.document("params").on_snapshot(update_conf)

    def oldget_mode(self):
        mode_doc = self.status.document("nav").get().to_dict()
        self.client.set('mode',mode_doc["mode"])

    def get_mode(self, actual):
        try:
            return self.client.get('mode').decode("utf-8")
        except:
            return actual
    
    def set_mode(self,modo):
        self.status.document("nav").update({"mode":modo})
        sleep(1)

    def get_ancho(self):
        ancho=self.conf.document("params").get().to_dict()["ancho"]
        return int(ancho)

    def get_centro(self):
        return int(self.conf.document("params").get().to_dict()["centro"])

    def set_actual(self,actual):
       self.client.set('steersensor',str(actual))

    def get_target(self):
        mode_doc = self.status.document("nav").get().to_dict()
        target=Coordinate( float(mode_doc["lat"]) , float(mode_doc["lon"]) )
        return target

    def load_route(self):
        mode_doc = self.mission.document("routes").get().to_dict()
        print("RUTA DE INTERNET")
        r=[]
        a=Coordinate(mode_doc["a"].latitude, mode_doc["a"].longitude)
        b=Coordinate(mode_doc["b"].latitude, mode_doc["b"].longitude)
        for point in mode_doc["nav"]:
            wgsp=Coordinate(point.latitude, point.longitude)
            utmp=utils.to_utm(wgsp)
            r.append(Point(utmp.x,utmp.y))
            print(utmp)
        return r,a,b
    def load_limit(self):
        mode_doc = self.mission.document("routes").get().to_dict()
        print("LIMITE DE INTERNET")
        r=[]
        a=Coordinate(mode_doc["a"].latitude, mode_doc["a"].longitude)
        b=Coordinate(mode_doc["b"].latitude, mode_doc["b"].longitude)
        for point in mode_doc["limit"]:
            wgsp=Coordinate(point.latitude, point.longitude)
            r.append(wgsp)
        return r,a,b


    def get_ip(self):
        mode_doc = self.conf.document("params").get().to_dict()
        return mode_doc["ip"]

    def set_ip(self,ip):
        self.conf.document("params").update({u'ip': ip})
    def get_test(self):
        mode_doc = self.status.document("nav").get().to_dict()
        self.status.document("nav").update({"step": "0", "dir": "0"})
        return mode_doc["step"], mode_doc["dir"]

    def set_limit(self,coords):
        nav=[]
        for cord in coords:
            nav.append(firestore.GeoPoint(cord.y, cord.x))
        self.mission.document("routes").update({u'limit': nav})
        self.status.document("nav").update({"mode":"STOP"})

    
    def set_wp(self,coords):
        nav=[]
        for cord in coords:
            coord=utils.to_wgs84(cord)
            nav.append(firestore.GeoPoint(coord.y, coord.x))
        self.mission.document("routes").update({u'nav': nav})
        self.status.document("nav").update({"mode":"STOP"})
    
    def set_a(self,coord):
        coord2 = firestore.GeoPoint(coord.y, coord.x)
        self.client.set('a_lat',str(coord.y))
        self.client.set('a_lon',str(coord.x))
        self.mission.document("routes").update({u'a': coord2})
        self.status.document("nav").update({"mode":"STOP"})

    def set_b(self,coord):
        coord2 = firestore.GeoPoint(coord.y, coord.x)
        self.client.set('b_lat',str(coord.y))
        self.client.set('b_lon',str(coord.x))
        self.mission.document("routes").update({u'b': coord2})
        self.status.document("nav").update({"mode":"CREAR RUTA"})

    def clear_mission(self):
        self.mission.document("routes").set({"nav": [], "limit": [],"a": None, "b": None})
    
    def clear_mission_wo(self):
        self.mission.document("routes").update({"nav": []})


