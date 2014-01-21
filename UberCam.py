import cv2
import datetime
import glob
import numpy as np
import time
import UberStep

imgDir = 'D:\\UberCam\\'
imgIndex = 0

# size of image region and overall window
displaySize = (800,600)
windowSize = (800,700)

# scaling of image, as per full camera resolution (needs calibration)
umPerPixel = 0.1341

# stepper motor distance per each full step
umPerStep = 500./1824/4;

# step magnitudes to be selected by number keys
stepAmts = [2,4,8]+[x/umPerStep for x in [1.0, 5.0, 25.0, 100.0, 500.0]]

# stepper motor movement distance, in steps, taken from the above array
stepperSteps = 2

# stepper motor backlash compensation
stepperBacklash = True




def imgRoot():
    # get timestamp as string
    d = datetime.datetime.today()
    return d.strftime("%Y-%m-%d")

def init(width, height):
    global imgIndex
    
    # figure out how many images we have already from today
    files =	 glob.glob(imgDir + imgRoot() + '.*.jpg')
    if files:
        maxnum = max(map(lambda x: int((x.split('.'))[1]), files))
        imgIndex = maxnum + 1
    
    print 'Starting file list at index ' + str(imgIndex)
    
    # create the camera
    cap = cv2.VideoCapture(0)
    cv2.namedWindow("UberCam", cv2.cv.CV_WINDOW_AUTOSIZE)
    cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,width)
    cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,height)
    time.sleep(1)
    cap.set(cv2.cv.CV_CAP_PROP_EXPOSURE,-4)
    
    return cap
    
    
def saveImage(img):
    global imgIndex
    
    fname = '{}{}.{:03d}.jpg'.format(imgDir,imgRoot(),imgIndex)
    cv2.imwrite(fname, img);
    print 'Saved ' + fname
    imgIndex = imgIndex + 1
    
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
    
def drawStepperInfo(img):
    '''Draws the current stepper motor position and whatnot'''
    ds = np.array(displaySize)
    ds[0] = 40
    ds[1] += 35
 
    # draw current stepper position
    stepperPos = np.array(stepper.position)*umPerStep
    for i in range(3):
        s = '%s: %0.2f um' % ('XYZ'[i],np.round(stepperPos[i],2))
        leftText(img, s, ds + np.array([0,20*i]))
    
    # draw text for current step number
    s = '%d steps (%0.2f um)' % (stepperSteps,np.round(stepperSteps*umPerStep,2))
    leftText(img, s, ds + np.array([200,20]))
 
if __name__ == '__main__':
    # main doesn't need global decls since this isn't a function!
    # i should probably wrap this in a function to avoid global scoping and stuff
    # but i'm not going to
    # and i'm not sorry
    
    cap = init(1600,1200)
    
    # get inital values
    _, frame = cap.read()
    height, width, _ = frame.shape
    
    # zoom center and amount
    zoomx = width/2
    zoomy = height/2
    zoom = 0
    
    # show inset sub-window view?
    subView = True
    subSize = (160,120)
    subPos = (displaySize[0]-subSize[0]-20,20)
    
    # and create an image to draw to screen
    windowImage = cv2.resize(frame, windowSize)
    
    # connect to stepper motors
    stepper = UberStep.Stepper(2)
    
    loop = True
    
    while(loop):
        # get next frame
        _, frame = cap.read()
        if (frame == None):
            print "Frame read error"
            break;
        # convert to grayscale from G channel
        frame[:,:,2] = frame[:,:,1]
        frame[:,:,0] = frame[:,:,1]
        #centeredText(frame,"foobar!",(800,600),fontScale=7)
        # calculate source box from captured image, based on current zoom value
        zoomBox = (width/(2**zoom),height/(2**zoom))
        # make sure we aren't over any of the edges
        zoomx = max(zoomx,zoomBox[0]/2)
        zoomy = max(zoomy,zoomBox[1]/2)
        zoomx = min(zoomx,width-zoomBox[0]/2)
        zoomy = min(zoomy,height-zoomBox[1]/2)
        # get the top-left of the zoombox
        zoomOrigin = (zoomx-zoomBox[0]/2,zoomy-zoomBox[1]/2)
        
        # clear the window
        windowImage.fill( (0,0,0) )
        
        # scale from zoombox to display size, and draw to window
        windowImage[0:displaySize[1],0:displaySize[0],:] = \
                cv2.resize(subImage(frame,zoomOrigin,zoomBox),displaySize)
                
        # should we draw the sub-window?
        if subView and (zoom > 0):
            windowImage[subPos[1]:subPos[1]+subSize[1],subPos[0]:subPos[0]+subSize[0],:] = \
                    cv2.resize(frame,subSize,interpolation=cv2.cv.CV_INTER_AREA)
            cv2.rectangle(windowImage,subPos,(subPos[0]+subSize[0],subPos[1]+subSize[1]),(255,255,255))
        
        drawScaleBar(windowImage)
        drawStepperInfo(windowImage)
        
        # display the image
        cv2.imshow("UberCam", windowImage)
        
        # make sure backlash is set if needed, to 1 um or so
        if (stepperBacklash):
            stepper.setBacklash(15)
        else:
            stepper.setBacklash(0)
    
        # update the stepper motor
        stepper.update()
        
        # get any keypresses
        char = cv2.waitKey(33)
        
        # scaling for zoom panning steps
        d = 128/2**zoom
        
        # ----- ONLY KEYBOARD HANDLING BELOW HERE -----
        
        if (char == 27):
            loop = False
        if (char == ord('p')):
            # opencv's hack to open camera settings panel
            cap.set(37, 1)
        if (char == ord(' ')):
            saveImage(frame)
        # zoom in and out
        if (char == ord('=') or char == ord('+')):
            zoom = min(zoom+1,4)
        if (char == ord('-')):
            zoom = max(zoom-1,0)
        
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
            
        # set number of steps using number keys
        if (char >= ord('1') and char <= ord('8')):
            stepperSteps = int(np.round(stepAmts[char-ord('1')]))
            
        # set whether motor is doing backlash compensation motion or not
        if (char == ord('B')):
            stepperBacklash = not stepperBacklash
            
        # stepper motor commands, uppercase for safety (no accidental keypress)
        if (char == ord('H')):
            stepper.homeAll()
        if (char == ord('Z')):
            stepper.setZero()
        # axis movement
        if (char == ord('A')):
            stepper.queueMove(0, stepperSteps)
        if (char == ord('D')):
            stepper.queueMove(0, -stepperSteps)
        if (char == ord('W')):
            stepper.queueMove(1, -stepperSteps)
        if (char == ord('S')):
            stepper.queueMove(1, stepperSteps)
        if (char == ord('Q')):
            stepper.queueMove(2, -stepperSteps)
        if (char == ord('E')):
            stepper.queueMove(2, stepperSteps)
            
    stepper.close()
    cap.release()
    cv2.destroyAllWindows()