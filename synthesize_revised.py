from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio
import random
import cv2 as cv
from sklearn.preprocessing import normalize
import math

"""
1. Synthesize points on 3d soccer field model and visualize
2. generate virtual images from synthesized data and model 
3. save the synthesize data into mat file
"""

"""
function to generate random points.
"""


def generate_points(num):
    list_pts = []
    for i in range(num):
        choice = random.randint(0, 4)
        if choice < 2:
            xside = random.randint(0, 1)
            list_pts.append([xside * random.gauss(0, 5) + (1 - xside) * random.gauss(108, 5),
                             random.uniform(0, 70), random.uniform(0, 10)])
        elif choice < 4:
            list_pts.append([random.uniform(0, 108), random.gauss(63, 2), random.uniform(0, 10)])
        else:
            tmpx = random.gauss(54, 20)
            while tmpx > 108 or tmpx < 0:
                tmpx = random.gauss(54, 20)

            tmpy = random.gauss(32, 20)
            while tmpy > 63 or tmpy < 0:
                tmpy = random.gauss(32, 20)

            list_pts.append([tmpx, tmpy, random.uniform(0, 1)])

    pts_arr = np.array(list_pts, dtype=np.float32)
    return pts_arr


pts = generate_points(10)

"""
function from 3d -> 2d
"""


def from_3d_to_2d(annotation, pos, base_r):
    camera = annotation['camera'][0]
    u = camera[0]
    v = camera[1]
    f = camera[2]
    k = np.array([[f, 0, u], [0, f, v], [0, 0, 1]])

    pan = annotation['ptz'].squeeze()[0] * math.pi / 180
    tilt = annotation['ptz'].squeeze()[1] * math.pi / 180

    rotation = np.dot(np.array([[1, 0, 0], [0, math.cos(tilt), math.sin(tilt)], [0, -math.sin(tilt), math.cos(tilt)]]),
                      np.array([[math.cos(pan), 0, -math.sin(pan)], [0, 1, 0], [math.sin(pan), 0, math.cos(pan)]]))
    rotation = np.dot(rotation, base_r)

    c = np.array(camera[6:9])
    pos = np.dot(k, np.dot(rotation, pos - c))

    return [pos[0] / pos[2], pos[1] / pos[2]]


"""
function from pan/tilt to 2d
"""

def from_pan_tilt_to_2d(annotation, pan, tilt):
    camera = annotation['camera'][0]
    u = camera[0]
    v = camera[1]
    f = camera[2]

    camera_pan = annotation['ptz'].squeeze()[0] * math.pi / 180
    camera_tilt = annotation['ptz'].squeeze()[1] * math.pi / 180

    x = f * math.tan(pan - camera_pan) + u
    y = -f * math.tan(tilt - camera_tilt) + v

    return [x, y]


"""
load the soccer field model
"""

soccer_model = sio.loadmat("./two_point_calib_dataset/util/highlights_soccer_model.mat")
line_index = soccer_model['line_segment_index']
points = soccer_model['points']

"""
load the sequence annotation
"""

seq = sio.loadmat("./two_point_calib_dataset/highlights/seq3_anno.mat")
annotation = seq["annotation"]
meta = seq['meta']

base_rotation = np.zeros([3, 3])
cv.Rodrigues(meta[0][0]["base_rotation"][0], base_rotation)


""" 
compute the rays of these synthesized points
"""

def compute_rays(proj_center, pos, base_r):
    relative = np.dot(base_r, np.transpose(pos - proj_center))
    x, y, z = relative

    pan = math.atan(x / (z))
    tilt = math.atan(-y / math.sqrt(x * x + z * z))
    return [pan, tilt]

proj_center = meta[0][0]["cc"][0]
rays = []

for i in range(0, len(pts)):
    # relative = np.dot(base_rotation, np.transpose(pts[i] - proj_center))
    #
    # x, y, z = relative
    # # print("rel", relative)
    # pan = math.atan(x / (z))
    # tilt = math.atan(-y / math.sqrt(x * x + z * z))
    # tilt = math.asin(relative[2] / np.linalg.norm(relative))

    # print("hello", pan * 180 / math.pi, tilt * 180 / math.pi)

    ray = compute_rays(proj_center, pts[i], base_rotation)

    rays.append(ray)

"""
This part is used to visualize the soccer model.
"""
fig = plt.figure(num=1, figsize=(10, 5))
ax = fig.add_subplot(111, projection='3d')

ax.set_xlim(0, 120)
ax.set_ylim(0, 70)
ax.set_zlim(0, 10)

for i in range(len(line_index)):
    x = [points[line_index[i][0]][0], points[line_index[i][1]][0]]
    y = [points[line_index[i][0]][1], points[line_index[i][1]][1]]
    z = [0, 0]
    ax.plot(x, y, z, color='g')

ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], color='r', marker='o')

plt.show()

"""
This part is used to show the synthesized images
"""

for i in range(annotation.size):

    img = np.zeros((720, 1280, 3), np.uint8)
    img.fill(255)
    camera = annotation[0][i]['camera'][0]

    k_paras = camera[0:3]
    k = np.array([[k_paras[2], 0, k_paras[0]], [0, k_paras[2], k_paras[1]], [0, 0, 1]])

    # rotation matrix
    rotation = np.zeros([3, 3])
    cv.Rodrigues(camera[3:6], rotation)

    # base position
    c = np.array(camera[6:9])
    image_points = np.ndarray([len(points), 2])

    # get points and draw lines
    for j in range(len(points)):
        p = np.array([points[j][0], points[j][1], 0])
        p = np.dot(k, np.dot(rotation, p - c))
        image_points[j][0] = p[0] / p[2]
        image_points[j][1] = p[1] / p[2]

    for j in range(len(line_index)):
        begin = line_index[j][0]
        end = line_index[j][1]
        cv.line(img, (int(image_points[begin][0]), int(image_points[begin][1])),
                (int(image_points[end][0]), int(image_points[end][1])), (0, 0, 255), 5)

    # draw the feature points in images
    for j in range(len(pts)):
        p = np.array(pts[j])
        res = from_3d_to_2d(annotation[0][i], p, base_rotation)
        res2 = from_pan_tilt_to_2d(annotation[0][i], rays[j][0], rays[j][1])

        if 0 < res[0] < 1280 and 0 < res[1] < 720:
            print("ray", rays[j][0] * 180 / math.pi, rays[j][1] * 180 / math.pi)
            print("res:, ", res)
            print("res2: ", res2)
            print("==========")
        # print("here")
        # print(res)
        # print(res2)
        # p = np.dot(k, np.dot(rotation, p - c))

        cv.circle(img, (int(res[0]), int(res[1])), color=(0, 0, 0), radius=8, thickness=2)

    cv.imshow("synthesized image", img)
    cv.waitKey(0)

"""
This part saves synthesized data to mat file
"""
key_points = dict()
features = []

# generate features randomly
for i in range(len(pts)):
    vec = np.random.random(16)
    vec = vec.reshape(1, 16)
    vec = normalize(vec, norm='l2')
    vec = np.squeeze(vec)
    features.append(vec)

key_points['features'] = features
key_points['pts'] = pts
key_points['rays'] = rays

sio.savemat('synthesize_data.mat', mdict=key_points)