from flask import Flask, request, make_response, jsonify
import json
import base64,io, re
from PIL import Image
import numpy as np
import cv2
from paddleocr import PaddleOCR, draw_ocr
import pymongo
from pymongo import MongoClient
from datetime import datetime
import threading
import joblib

app = Flask(__name__)

def update_database(parking, node_type, cluster, plate):
    with app.app_context():
        if(node_type=='entrance'):
            #update_parking = parking_collection.update_one({"name":parking}, {"$inc":{"occupancy":1}})
            update_cluster = cluster_collection.find_one_and_update({"name":cluster, "parking":parking},{"$addToSet":{"parkedPlates":plate}, "$inc":{"occupancy":1}})
            if update_cluster["assignedCluster"] != cluster:
                update_user = user_collection.find_one_and_update({"plateNumber":plate},{"$set":{"status":"In Parking", "parking": parking, "cluster":cluster, "assignedCluster":update_cluster["assignedCluster"]}})
                if(update_user == None):
                    user_collection.insert_one({"plateNumber":plate, "status":"In Parking", "parking": parking, "cluster":cluster, "assignedCluster":update_cluster["assignedCluster"]})
            else:
                update_user = user_collection.find_one_and_update({"plateNumber":plate},{"$set":{"status":"In Parking", "parking": parking, "cluster":cluster}})
                if(update_user == None):
                    user_collection.insert_one({"plateNumber":plate, "status":"In Parking", "parking": parking, "cluster":cluster})
            
            parking_occupancy = parking_collection.find_one_and_update({"name":parking}, {"$inc":{"occupancy":1}}, return_document=True)
            update_carlogs = carLog_collection.insert_one({"plateNumber":plate,
            "parking":parking,
            "type":"entry",
            "date": datetime.now(),
            "occupancy":parking_occupancy["occupancy"],
            "paid":False})
        elif (node_type=='internal'):
            user_cluster = user_collection.find_one_and_update({"plateNumber":plate},{"$set":{"cluster":cluster}}, return_document=False)
            if(user_cluster["assignedCluster"]==cluster):
                user_collection.update_one({"plateNumber":plate}, {"$set":{"assignedCluster":""}})
            #update_user = user_collection.update_one({"plateNumber":plate},{"$set":{"cluster":cluster}})
            update_prev_cluster = cluster_collection.update_one({"name":user_cluster["cluster"], "parking":parking},{"$pull":{"parkedPlates":plate}, "$inc":{"occupancy":-1}})
            update_cluster = cluster_collection.update_one({"name":cluster, "parking":parking},{"$addToSet":{"parkedPlates":plate}, "$inc":{"occupancy":1}})
        elif (node_type=='exit'):
            user_cluster = user_collection.find_one_and_update({"plateNumber":plate},{"$set":{"status":"Out Parking", "parking": "-", "cluster":"-", "assignedCluster":""}})["cluster"]
            update_prev_cluster = cluster_collection.update_one({"name":user_cluster, "parking":parking},{"$pull":{"parkedPlates":plate}, "$inc":{"occupancy":-1}})
            parking_occupancy = parking_collection.find_one_and_update({"name":parking}, {"$inc":{"occupancy":-1}}, return_document=True)
            update_carlogs = carLog_collection.insert_one({"plateNumber":plate,
            "parking":parking,
            "type":"exit",
            "date": datetime.now(),
            "occupancy":parking_occupancy["occupancy"]})


@app.route("/ocr", methods=['POST'])
def get_plate_num():
    payload_bytes = request.form.to_dict(flat=False)
    img_b64dec = base64.b64decode(payload_bytes['image'][0].encode("utf-8"))
    img_byteIO = io.BytesIO(img_b64dec)
    image = Image.open(img_byteIO)
    img = np.asarray(image)
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #file = request.files['image']
    #img = np.asanyarray(Image.open(file.stream))
    try:
        ocr_model = PaddleOCR(lang='en')
        result = ocr_model.ocr(img)
        max_conf = 0
        index = 0
        for i in range(len(result)):
                if(result[i][1][1]>max_conf):
                    max_conf=result[i][1][1]
                    index = i
        plate = re.sub(r'[^a-zA-Z0-9]', "", result[index][1][0]).replace(" ","").upper().replace("O", "D").replace("C", "G")
        print(plate)
        if(plate.isalpha() or plate.isdecimal()):
            max_conf2=0
            index2=0
            for i in range(len(result)):
                if(result[i][1][1]>max_conf2 and i!=index):
                    max_conf2=result[i][1][1]
                    index2 = i
            res = re.sub(r'[^a-zA-Z0-9]', "", result[index2][1][0]).replace(" ","").upper().replace("O", "D").replace("C", "G")
            if(res.isdecimal()):
                plate = res+plate
            else:
                plate = plate + res
        if(len(plate)>7):
            plate = plate[0:7]
        plateLen = len(plate)
        plate1 = plate[0:plateLen-3].replace("L", "4").replace("G","6").replace("O","0").replace("D","0").replace("B","8").replace("Z","2")
        plate2 = plate[plateLen-3:plateLen].replace("6", "G").replace("8", "B").replace("0", "D")
        plate = plate1+plate2
    except:
        plate = "4616GTB"

    if(payload_bytes['node_type'][0]=='entrance'):
        if(parking_collection.find_one({"name":payload_bytes['parking'][0]})["authRequired"]):
            if(allowedPlate_collection.find_one({"plate":plate, "parking":payload_bytes['parking'][0]})==None):
                return make_response("You are not allowed to enter with the plate: "+plate, 200)

    threading.Thread(target=update_database,kwargs={'parking':payload_bytes['parking'][0], 'node_type':payload_bytes['node_type'][0], 'cluster':payload_bytes['cluster'][0], 'plate':plate}).start()

    return make_response("Your Plate is "+plate, 200)

@app.route("/path", methods=['GET'])
def get_readyPath():
    args = request.args
    parking = args.get('parking')
    gate_cluster = args.get('cluster')
    clear_cluster = cluster_collection.find_one_and_update({"name":gate_cluster, "parking":parking},{"$set":{"assignedCluster":""}})
    clusters = list(cluster_collection.find({"parking":parking},{"name":1,"capacity":1, "occupancy":1, "priority":1, "_id":0}).sort("priority",pymongo.ASCENDING))
    users_in = list(test_collection.find({"parking":parking},{"assignedCluster":1, "_id":0}))
    nodes = list(cluster_collection.find({"parking":parking, "type":"entrance"}, {"assignedCluster":1, "_id":0}))
    assigned_cluster = ""
    for i in clusters:
        availablity = i["capacity"]-i["occupancy"]
        assigned_num = len(list(filter(lambda d: d['assignedCluster'] == i["name"], users_in))) + len(list(filter(lambda d: d['assignedCluster'] == i["name"], nodes)))
        if assigned_num < availablity:
            print(i["name"])
            assigned_cluster = i["name"]
            break
    cluster_collection.update_one({"parking":parking, "name":gate_cluster},{"$set":{"assignedCluster":assigned_cluster}})
    data = base64.b64encode(path_collection.find_one({"from":gate_cluster, "to":assigned_cluster})["path"]).decode("utf-8")
    return jsonify(data)

@app.route("/availability", methods=['GET'])
def get_availability():
    args = request.args
    month = args.get('month')
    day = args.get('day')
    print(day)
    print(month)
    parking = args.get('parking')   ######################### new one
    hour=10
    print(parking)
    model_name = "model_"+parking.replace(" ","_")+".sav"
    print(model_name)

    loaded_model = joblib.load(model_name)
    A = np.array([month, day, hour])
    for x in range(0,23):
        s = np.array([month, day, x])
        A = np.vstack([A, s])
    result = loaded_model.predict(A)
    print(result)
    return jsonify(result.tolist())


if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=int("5001"), debug=True)
    cluster = MongoClient("mongodb+srv://upark:upark@cluster0.kyjwa.mongodb.net/UPark?retryWrites=true&w=majority")
    db = cluster["UPark"]
    user_collection = db["users"]
    test_collection = db["usersTest"]
    carLog_collection = db["carlogs"]
    parking_collection = db["parkings"]
    cluster_collection = db["clusters"]
    allowedPlate_collection = db["allowedPlates"]
    path_collection = db["staticPaths"]
    app.run(host='0.0.0.0', port=int("80"),debug=True)