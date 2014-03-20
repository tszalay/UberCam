import serial
import time

# the two states in the "state machine", not worth using an enum
ST_IDLE = 0
ST_BUSY = 1

# possible commands sent back and forth. chosen arbitrarily, of course
CMDS = {'ACK':57, 'SLOW':11, 'FAST':22, 'HOME':33, 'ABORT':17}

class Stepper():
    def __init__(self, port=0):
        # current state
        self.curState = ST_IDLE
        
        # last time we moved
        self.lastMove = time.time()
        
        # the queue of commands we are waiting to send.
        # each element is a tuple of (cmd, axis, steps)
        # the top element is the one being processed; gets removed when we get an ack
        self.cmdQueue = []
        
        # the number of anti-backlash steps to take
        self.backlash = 0
        
        # current position, in steps
        self.position = [0,0,0]
        
        # and connect to the stepper motor
        self.ser = serial.Serial(port, 57600)
        print "Connected on port " + self.ser.name
        
    def isBusy(self):
        return (self.curState == ST_BUSY)
    
    def timeSinceMoved(self):
        if (self.isBusy()):
            return 0
        return time.time() - self.lastMove
        
    def update(self):
        '''Check for acks, transmit commands if necessary, etc'''
        # did we get anything from the motors?
        if (self.ser.inWaiting() > 0):
            b = self.ser.read()
            b = ord(b)
            # if we got an ack, we are again idle
            if (b == CMDS['ACK']):
                self.curState = ST_IDLE
                self.lastMove = time.time()
                print 'ACK'
                # delete first element in list, make sure it's there
                if self.cmdQueue:
                    cmd = self.cmdQueue[0]
                    self.cmdQueue = self.cmdQueue[1:]
                    # update position, if we have to
                    if (cmd[0] == 'SLOW' or cmd[0] == 'FAST'):
                        self.position[cmd[1]] += cmd[2]
                    if (cmd[0] == 'HOME'):
                        self.position[cmd[1]] = 0
            else:
                # clear buffer, ack is the only command we should be receiving
                print "Unknown command received: " + str(b)
                while (self.ser.inWaiting() > 0):
                    b = self.ser.read()
                    print str(b)
                self.ser.flushInput()
                self.cmdQueue = []
                self.curState = ST_IDLE
        
        # do we have any pending commands? if so, and idle, send next one
        self.sendCommand()
        
    def setBacklash(self, nBacklash):
        '''Set number of anti-sticking/anti-backlash steps to take'''
        self.backlash = nBacklash
        
    def queueMove(self, axis, steps):
        '''Moves stepper on an axis, taking note of current backlash settings'''
        if (self.backlash > 0):
            self.queueCommand('SLOW',axis,self.backlash)
        self.queueCommand('SLOW',axis,steps-self.backlash)
    
                
    def queueCommand(self, command, axis, steps):
        '''Add this command to the queue'''
        self.cmdQueue.append((command,axis,steps))
        
    
    def sendCommand(self):
        '''Send the next command in the queue, and wait for ack'''
        # only send if we're ready and have a command to send
        if (self.curState != ST_IDLE or not self.cmdQueue):
            return False
        
        # we are busy until we get an ack from the motor
        self.curState = ST_BUSY
        
        cmd = self.cmdQueue[0]
        command = cmd[0]
        axis = cmd[1]
        steps = cmd[2]
        
        # get ready to write
        # bytes are command, axis, and then bytes of steps
        data = bytearray([CMDS[command], axis] + [255&(steps >> (8*i)) for i in range(4)])
        # write it
        self.ser.write(data)
        
        # and display it
        print command + "(" + str(axis) + "): " + str(steps)
        
        return True
    
        
    def sendAbort(self):
        # do not pass go, do not care about state, etc etc abort NOW, flush queue
        self.ser.write(bytearray([CMDS['ABORT'],0]))
        self.curState = ST_IDLE
        self.cmdQueue = []
        
        print 'ABORT SENT'
        
        
    def setZero(self):
        '''Set zero at current position'''
        self.position = [0,0,0]
        
    
    def homeAll(self):
        '''Home all three axes, in order'''
        self.queueCommand('HOME',2,0)
        self.queueCommand('HOME',0,0)
        self.queueCommand('HOME',1,0)
        
        
    def close(self):
        self.ser.close()