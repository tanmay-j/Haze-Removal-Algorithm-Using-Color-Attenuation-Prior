import cv2 
import numpy as np
import copy 

def quantization(pixels, bins,range_):
    m = range_[0]
    interval_size = range_[1]-range_[0]
    interval_size/=bins

    for i in range(len(pixels)):
        for j in range(len(pixels[i])):
            pixels[i][j] = ((pixels[i][j]-m)/interval_size)

           
    return pixels
def visualise(depth_map,name,beta):
    d = copy.deepcopy(depth_map)
    d = quantization(d,255,[d.min(),d.max()]).astype(np.uint8)

    d = cv2.applyColorMap(d, cv2.COLORMAP_HOT)
    cv2.imwrite("./output/"+name+ "_"+str(beta)+".jpg",d)

def relu(x):
    if x<0:
        return 0
    else:
        return x
def reverse_relu(bound,x):
    if x>bound:
        return bound
    else:
        return x

def guided_filter(image, g_image, eps = 0):
    blur_factor = (50,50)
    mean_i = cv2.blur(image,blur_factor)
    mean_g = cv2.blur(g_image,blur_factor)

    corr_gi = cv2.blur(g_image*image,blur_factor)
    corr_gg = cv2.blur(g_image*g_image,blur_factor)

    var_g = corr_gg - mean_g*mean_g
    cov_gi = corr_gi - mean_g*mean_i

    a = cov_gi / (var_g + eps)
    b = mean_i - (a*mean_g)

    mean_a = cv2.blur(a,blur_factor)
    mean_b = cv2.blur(b,blur_factor)

    q = mean_a * g_image + mean_b

    return q

# Variables
filename = "./images/forest.jpg"
noise = 0 # guided filter, eps
beta = 1 #dehazing strength

# Theta values
theta0 = 0.121779
theta1 = 0.959710
theta2 = -0.780245
sigma = 0.041337

n_size = 5 # Size of neighbourhood considered for min filter
blur_strength = 15 # Strength of blurring after min filter in depthmap

# Reading the image
h_img = cv2.imread(filename)

#Extracting the value and saturation values from the image
hsv = cv2.cvtColor(h_img, cv2.COLOR_BGR2HSV)
value = hsv[:,:,2].astype('float')/255 # Intensity values of image
saturation = hsv[:,:,1].astype('float')/255 # Saturation values of image

# Calculating the depth map
depth_map = theta0 + theta1*value + theta2*saturation + np.random.normal(0,sigma, hsv[:,:,0].shape)
visualise(depth_map,"1_depth_map",beta)

#Calculating the min-filtered depth map
new_depth_map = copy.deepcopy(depth_map)

width = depth_map.shape[1]
height = depth_map.shape[0]

for i in range(height):
    for j in range(width):
        x_low = relu(i-n_size)
        x_high =  reverse_relu(height-1,i+n_size)+1
        y_low = relu(j-n_size)
        y_high =  reverse_relu(width-1,j+n_size)+1
        new_depth_map[i][j] = np.min( depth_map[x_low:x_high,y_low:y_high] )

visualise(new_depth_map,"2_min_filter_depth_map",beta)


# Refining the depth map
# blurred_depth_map = cv2.GaussianBlur(new_depth_map,(blur_strength,blur_strength),0) # Gaussian blur of depthmap (d(x))
blurred_depth_map = guided_filter(new_depth_map,depth_map,noise)
visualise(blurred_depth_map,"3_blurred_depth_map",beta)


# Restoring scene radiance
depth_map_1d = np.ravel(blurred_depth_map)
rankings = np.argsort(depth_map_1d)

threshold = (99.9*len(rankings))/100
indices = np.argwhere(rankings>threshold).ravel()

indices_image_rows = indices//width
indices_image_columns = indices % width

atmospheric_light = np.zeros(3) # A
intensity = -np.inf
for x in range(len(indices_image_rows)):
    i = indices_image_rows[x]
    j = indices_image_columns[x]

    if value[i][j] >= intensity:
        atmospheric_light = h_img[i][j]
        intensity = value[i][j]

t = np.exp(-beta*blurred_depth_map)

denom = np.clip(t,0.1,0.9)
numer = h_img.astype("float") - atmospheric_light.astype("float")

output_image = copy.deepcopy(h_img).astype("float")

for i in range(len(output_image)):
    for j in range(len(output_image[i])):
        output_image[i][j] = numer[i][j]/denom[i][j]
    
output_image += atmospheric_light.astype("float")
output_image[:,:,0] = quantization(output_image[:,:,0],256,[np.min(output_image[:,:,0]),np.max(output_image[:,:,0])])
output_image[:,:,1] = quantization(output_image[:,:,1],256,[np.min(output_image[:,:,1]),np.max(output_image[:,:,1])])
output_image[:,:,2] = quantization(output_image[:,:,2],256,[np.min(output_image[:,:,2]),np.max(output_image[:,:,2])])

# print(numer.shape)
# print(denom.shape)
# print(output_image.shape)

cv2.imwrite("./output/hazy_"+str(beta)+".jpg",h_img)
cv2.imwrite("./output/dehazy_"+str(beta)+".jpg",output_image)