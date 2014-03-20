import numpy as np
import cv2

# size of target region, in x-y
TgtSize = np.array((200,600))

class Target:
    '''Class for tracking position of subregion in a camera image'''
    
    def __init__(self):
        '''Initialize internal images and variables (and KF)'''
        self._loc = np.zeros(2)
        self._orig = np.zeros(2)
        # large and small templates
        self._tgtbig = np.zeros(TgtSize[::-1],np.uint8)
        self._tgtsmall = np.zeros(TgtSize[::-1]/4,np.uint8)
        
    def setTarget(self,img,center):
        '''Sets target image based on given center coordinate'''
        loc = np.array(center)
        ul = loc - TgtSize/2
        br = loc + TgtSize/2 
        if (np.any(ul < 0) or np.any(br >= np.array(img.shape[::-1]))):
            return
        
        self._tgtbig = img[ul[1]:br[1],ul[0]:br[0]]
        self._tgtsmall = cv2.resize(self._tgtbig,tuple(TgtSize/4))
        self._loc = loc.copy()
        self._orig = loc.copy()
    
    def findMatch(self, imgbig, imgsmall):
        '''Find position of best match, need big and small (/4) versions of image'''
        
        # match the template, small first
        tmp = cv2.matchTemplate(imgsmall,self._tgtsmall,cv2.cv.CV_TM_SQDIFF_NORMED)
        # get position of minimum, in the shrunken image
        loc = np.array(cv2.minMaxLoc(tmp)[2])
        # scale to full image
        loc = loc*4+TgtSize/2
        # extend the search a bit past just the target size
        d = 24
        sz = TgtSize+d
        # upper-left and lower-right points, in pixel coords
        ul = loc - sz/2
        br = loc + sz/2
        # make sure we aren't out of bounds
        szfull = np.array(imgbig.shape[::-1])
        ul = np.clip(ul,0,szfull)
        br = np.clip(br,0,szfull)
        
        # now find the best match in the full-size image
        tmp = cv2.matchTemplate(imgbig[ul[1]:br[1],ul[0]:br[0]],self._tgtbig,cv2.cv.CV_TM_SQDIFF_NORMED)
        lbig = np.array(cv2.minMaxLoc(tmp)[2])
        # and recenter to full image
        loc = ul + lbig + TgtSize/2
        
        
        return loc