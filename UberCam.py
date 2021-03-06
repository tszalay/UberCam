import cv2
import datetime
import glob
import numpy as np
import time
import subprocess as sp
import pdb

import uc480


imgDir = 'C:\\UberCam\\'
imgIndex = 0

# size of image region and overall window
displaySize = (800,600)
windowSize = (800,700)

# scaling of image, as per full camera resolution
umPerPixel = 0.113*5


ff_command = ['ffmpeg.exe',
        '-y', # (optional) overwrite output file if it exists
        '-f', 'rawvideo',
        '-vcodec','rawvideo',
        '-s', '1024x768', # size of one frame
        '-pix_fmt', 'gray',
        '-r', '20', # frames per second
        '-an', # Tells FFMPEG not to expect any audio
        '-i', '-', # The imput comes from a pipe        
#        '-vcodec', 'libx264',
        '-vcodec', 'mjpeg',
        'my_output_videofile.avi']



def imgRoot():
    # get timestamp as string
    d = datetime.datetime.today()
    return d.strftime("%Y-%m-%d")

def init():
    global imgIndex
    
    # figure out how many images we have already from today
    files =	 glob.glob(imgDir + imgRoot() + '.*.???')
    if files:
        maxnum = max(map(lambda x: int((x.split('.'))[1]), files))
        imgIndex = maxnum + 1
    
    print 'Starting file list at index ' + str(imgIndex)
    
    # create the ThorLabs camera
    camera = uc480.camera()
    camera.AllocImageMem()
    camera.SetImageMem()
    camera.SetImageSize()
    camera.SetColorMode()
    camera.SetPixelClock(20)
    
    camera.SetGamma(160)
    
    if 0:
        camera.SetGain(1)
        camera.SetExposureTime(10)
        camera.SetFrameRate(20)
    else:
        camera.SetGain(1)
        camera.SetExposureTime(2)
        camera.SetFrameRate(20)
        #camera.SetGainBoost()
        
    camera.CaptureVideo()
    
    cv2.namedWindow("UberCam", cv2.cv.CV_WINDOW_AUTOSIZE)
    
    return camera
    
    
def saveImage(img):
    global imgIndex
    
    fname = '{}{}.{:03d}.jpg'.format(imgDir,imgRoot(),imgIndex)
    cv2.imwrite(fname, img);
    print 'Saved ' + fname
    imgIndex = imgIndex + 1
    
def nextVideo():
    global imgIndex
    
    fname = '{}{}.{:03d}.avi'.format(imgDir,imgRoot(),imgIndex)
    imgIndex = imgIndex + 1
    
    return fname
    
def cvPt(pt):
    '''Format a point in OpenCV-appropriate int-tuple'''
    return tuple(map(int,pt))
    
def subImage(img, origin, size):
    '''Return sub-image by top-left coords and w/h (tuples)'''
    return img[origin[1]:origin[1]+size[1],origin[0]:origin[0]+size[0]]
    
def centeredText(img, text, origin, fontFace=cv2.cv.CV_FONT_HERSHEY_DUPLEX, fontScale=0.5):
    '''Draw centered text on an image'''
    textSize,_ = cv2.getTextSize(text, fontFace, fontScale, 1)
    
    cv2.putText(img, text, (origin[0]-textSize[0]/2,origin[1]+textSize[1]/2), \
        fontFace, fontScale, (255,255,255), 1, cv2.cv.CV_FILLED)
        
def leftText(img, text, origin, fontFace=cv2.cv.CV_FONT_HERSHEY_DUPLEX, fontScale=0.5):
    '''Draw left-aligned text on an image'''
    cv2.putText(img, text, tuple(origin), \
        fontFace, fontScale, (255,255,255), 1, cv2.cv.CV_FILLED)
    
def drawScaleBar(img):
    '''Draw a scale bar on the screen, right below the image'''
    ds = np.array(displaySize)
    
    cv2.line(img, (0,ds[1]),(ds[0],ds[1]), (255,255,255))
    
    # the bar
    cv2.rectangle(img, tuple(ds+np.array([-250,20])), \
        tuple(ds+np.array([-50,25])), (255,255,255), cv2.cv.CV_FILLED)
    # and the label
    ums = umPerPixel * 200 / 2**zoom
    centeredText(img, '{:3.1f} um'.format(ums), tuple(ds+np.array([-150, 40])))


if __name__ == '__main__':
    # main doesn't need global decls since this isn't a function!
    # i should probably wrap this in a function to avoid global scoping and stuff
    # but i'm not going to
    # and i'm not sorry
    
    camera = init()
    width,height = (1024,768)
    
    # image gain
    gain = 1;

    # zoom center and amount
    zoomx = width/2
    zoomy = height/2
    zoom = 0
    
    # show inset sub-window view?
    subView = True
    subSize = (160,120)
    subPos = (displaySize[0]-subSize[0]-20,20)
    
    # are we doing a running average?
    doAverage = False
    # how many frames to store
    avgCount = 10
    # which index are we on in rotating buffer?
    avgIndex = 0
    # current image
    avgFrame = np.zeros((height,width),np.uint8)
    newAvgFrame = np.zeros((height,width),np.uint8)

    # variable for recording video    
    video = None
    
    # and create an image to draw to screen
    windowImage = np.zeros(windowSize[::-1],np.uint8)
    
    # create the window and set mouse callback
    # pass target image list as special param so we can write it
    cv2.namedWindow('UberCam')
    
    loop = True
    
    lastFrameNum = -1
    
    while(loop):
        while camera.GetFrameCount() == lastFrameNum:
            pass
        lastFrameNum = camera.GetFrameCount()
        time.sleep(0.010)
        
        # get next frame (by ref...)
        camera.CopyImageMem()
        curimg = camera.data
        
        # calculate source box from captured image, based on current zoom value
        zoomBox = (width/(2**zoom),height/(2**zoom))
        # make sure we aren't over any of the edges
        zoomx = max(zoomx,zoomBox[0]/2)
        zoomy = max(zoomy,zoomBox[1]/2)
        zoomx = min(zoomx,width-zoomBox[0]/2)
        zoomy = min(zoomy,height-zoomBox[1]/2)
        # get the top-left of the zoombox
        zoomOrigin = (zoomx-zoomBox[0]/2,zoomy-zoomBox[1]/2)
        
                
        # always have average running
        newAvgFrame = newAvgFrame + (curimg/float(avgCount))
        avgIndex = (avgIndex+1) % avgCount
        if (avgIndex == 0):
            # got through an entire cycle, update avg frame
            avgFrame = newAvgFrame.copy()
            newAvgFrame.fill(0)

        # but only display when we gotsa
        if (doAverage):
            curimg = avgFrame

        # clear the window
        windowImage.fill(0)
        
        # scale from full image to display size, and draw to window
        windowImage[0:displaySize[1],0:displaySize[0]] = \
                cv2.resize(subImage(curimg,zoomOrigin,zoomBox),displaySize)
                
        # should we draw the zoombox sub-window?
        if subView and (zoom > 0):
            windowImage[subPos[1]:subPos[1]+subSize[1],subPos[0]:subPos[0]+subSize[0]] = \
                    cv2.resize(curimg,subSize,interpolation=cv2.cv.CV_INTER_AREA)
            cv2.rectangle(windowImage,subPos,(subPos[0]+subSize[0],subPos[1]+subSize[1]),(255,255,255))
        
        drawScaleBar(windowImage)
        
        # display the image
        cv2.imshow("UberCam", windowImage)
        
        # get any keypresses
        char = cv2.waitKey(10)
        
        # scaling for zoom panning steps
        d = 128/2**zoom
        
        # ----- ONLY KEYBOARD HANDLING BELOW HERE -----
        
        if (char == 27):
            loop = False
        if (char == ord(' ')):
            saveImage(curimg)
        # zoom in and out
        if (char == ord('=') or char == ord('+')):
            zoom = min(zoom+1,4)
        if (char == ord('-')):
            zoom = max(zoom-1,0)
            
        # gain functions
        if (char == ord('.')):
            gain = min(gain+10,100)
            camera.SetGain(gain)
        if (char == ord(',')):
            if (gain < 10):
                gain = max(gain-1,1)
            else:    
                gain = max(gain-10,10)
            camera.SetGain(gain)
        if (char == ord('a')):
            camera.SetGain()
        
        # move zoom window around
        # don't ask me where the arrow key codes come from.... 0_o
        if (char == 2490368):
            zoomy = zoomy-d
        if (char == 2621440):
            zoomy = zoomy+d
        if (char == 2424832):
            zoomx = zoomx-d
        if (char == 2555904):
            zoomx = zoomx+d
            
        # toggle recording
        if (char == ord('R') or char == ord('r')):
            if video is None:
                ff_command[-1] = nextVideo()
                #ff_command[-2] = ff_command[-1] + '.raw'
                video = sp.Popen(ff_command, stdin=sp.PIPE, stdout=open('foo.txt','w'), stderr=open('foe.txt','w'))
                #video = open(ff_command[-2],'wb')
                print 'Started recording at %d fps' % int(camera.fps)
                #video = cv2.VideoWriter(nextVideo(), -1, int(camera.fps), (width, height))
                #if not video.isOpened():
                #    print 'Failed to open video stream!'
            else:
                #video.release()
                video.stdin.close()
                if video.stderr is not None:
                    video.stderr.close()
                video.wait()
#                video.close()
                video = None
                print 'Stopped recording'

        # save image
        if video is not None:
            #video.write(curimg)
            #pdb.set_trace()
            #video.communicate(curimg.tostring())
            video.stdin.write( curimg.tostring() )
#            video.stdin.flush()
            #print video.stderr.read()
#            video.write( curimg.tostring() )
            
        
        # toggle running average mode
        if (char == ord('Y') or char == ord('y')):
            doAverage = not doAverage
            if (doAverage):
                # we just started averaging, set array to current frame
                avgIndex = 0
                avgFrame = curimg.copy()
                newAvgFrame = curimg.copy()
                newAvgFrame.fill(0)
                            
    
    if video is not None:
        video.terminate()
        
    camera.StopLiveVideo()
    camera.FreeImageMem()
    camera.ExitCamera()
    cv2.destroyAllWindows()