
from PIL import Image #need to install: pip install pillow
import imagehash #need to install: sudo pip install imagehash
import os

targetImageName='/Users/gyl/Desktop/insight_projects/test_image_proc/image3.jpg'
hash1=imagehash.phash(Image.open(targetImageName))
hash1Str=str(hash1)

def hamming2(s1, s2):
    """Calculate the Hamming distance between two bit strings"""
    #assert len(s1) == len(s2)
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))

for imageFile in os.listdir('/Users/gyl/Desktop/insight_projects/test_image_proc/frames'):
    #print("hi")
    if imageFile.endswith('.jpg'):
        fileName='./frames/'+imageFile
        hash2=imagehash.phash(Image.open(fileName))
        hash2Str=str(hash2)
        hammingDist=hamming2(hash1Str,hash2Str)
        print(fileName, ",",hammingDist)
        #print(hammingDist)
