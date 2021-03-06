#!/usr/bin/env python
"""Gprowl

A Python script that connects to Gmail in IMAP's IDLE mode and pushes new messages to an iPhone using Prowl.

Requirements:
    Python 2.5 or greater
    OpenSSL 0.9.8j or greater
    Prowl iPhone application
    
Usage: python gprowl.py [options]

Options:
    -h, --help                Show this help
    -a ..., --api=...         Prowl API key
    -r ..., --priority=...    Prowl message priority
    -b ..., --bodyLength=...  Prowl message body length
    -u ..., --username=...    Gmail username
    -p ..., --password=...    Gmail password
    -l ..., --location=...    Location of openssl
    
Example:
    python gprowl.py
    python gprowl.py -a <YOUR_API_KEY> -u <YOUR_GMAIL_USERNAME> -p <YOUR_GMAIL_PASSWORD>
"""

__author__ = "Christopher T. Cannon (christophertcannon@gmail.com)"
__version__ = "0.9.9"
__date__ = "2009/10/11"

import sys
import subprocess
import getopt
import time

# Prowl API Key
apiKey = ""
# Prowl API URL
prowlUrl = "prowl.weks.net"
# Prowl Message Priority
priority = 0
# Prowl Body Length
bodyLength = 1000
# Gmail user name
username = ""
# Gmail password
password = ""
# openssl location
openssl = "/usr/bin/openssl"
# IMAP connection command
cmd = [openssl, "s_client", "-connect", "imap.gmail.com:993", "-crlf"]
# Connection restart interval
# 15 minutes in seconds
timeOutInterval = 900
# Previous email's ID
previousId = ""

class GmailIdleNotifier:
    def __init__(self):
        self.p = None
        self.timer = None
        self.checkClient()
        self.checkConnection()
        
        if(len(apiKey) == 0):
            self.getProwlApiKey()
            
        if(len(username) == 0):
            self.getGmailUserName()
            
        if(len(password) == 0):
            self.getGmailPassword()
            
        self.checkGmailCredentials()
    
    def checkClient(self):
        """Determines if the OpenSSL path is valid."""
        global openssl
        import os
        
        if(not os.path.isfile(openssl)):
            print "The OpenSSL path is not valid."
            sys.exit(1)
    
    def checkConnection(self):
        """Determines if the system has an Internet connection available."""
        import urllib2
        try:
            urllib2.urlopen("http://www.google.com")
        except:
            print "An Internet connection is not available."
            sys.exit(1)
        
    def getProwlApiKey(self):
        """Promt the user and verify their Prowl API key."""
        global apiKey, prowlUrl
        
        loop = True
        while(loop):
            key = raw_input("Prowl API key: ")
            import httplib
            headers = {"Content-type": "application/x-www-form-urlencoded",
            'User-Agent': "Gprowl/%s" % str(__version__)}

            path = "/publicapi/verify?apikey=%s" % key
            conn = httplib.HTTPSConnection(prowlUrl)
            conn.request("GET", path, "", headers)
            response = conn.getresponse()

            if("401" in str(response.status)):
                print "The API key entered is not valid."
                print "Please re-enter the API key."
            elif("200" in str(response.status)):
                apiKey = key
                loop = False
                
            conn.close()
                     
    def getGmailUserName(self):
        """Get the user's Gmail username."""
        global username
        username = raw_input("Gmail User Name: ")
        
    def getGmailPassword(self):
        """Get the user's Gmail password."""
        global password
        import getpass
        password = getpass.getpass("Gmail Password: ")
        
    def checkGmailCredentials(self):
        """Prompt the user and verify their Gmail credentials."""
        global username, password
        
        loop = True
        while(loop):
            global cmd
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            line = p.stdout.readline()
            while(line != None):
                # Input the credentials
                if("* OK Gimap ready" in line):
                    p.stdin.write(". login %s %s\n" % (username, password))
                # Credentials are valid
                elif("authenticated (Success)" in line):
                    print "Successful authentication..."
                    loop = False
                    break
                elif("Invalid credentials" in line):
                    print "The Gmail username or password entered is invalid."
                    print "Please re-enter the Gmail username and password."
                    self.getGmailUserName()
                    self.getGmailPassword()
                    break
                
                line = p.stdout.readline()
            
            # Kill the subprocess
            import os
            import signal
            os.kill(p.pid, signal.SIGTERM)
            
    
    def start(self):
        """Log into the Google IMAP server and enable IDLE mode."""
        global cmd

        # Start the timer to keep alive the OpenSSL subprocess
        import threading
        self.timer = threading.Timer(timeOutInterval, self.keepAlive)
        self.timer.start()
        
        # Start the openssl process
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
        idleMode = False
        global username, password, previousId
        line = self.p.stdout.readline()
        while(line != ""):
            # Input the credentials
            if("* OK Gimap ready" in line):
                self.p.stdin.write(". login %s %s\n" % (username, password))
            # Select the INBOX
            elif("authenticated (Success)" in line):
                self.p.stdin.write(". examine INBOX\n")
            # Invalid command line credentials
            elif("Invalid credentials" in line):
                print "Invalid Gmail credentials..."
                sys.exit(1)
            # Start IDLE mode
            elif("INBOX selected. (Success)" in line):
                self.p.stdin.write(". idle\n")
                idleMode = True
            # If IDLE mode is True and the email ID was not
            # previously sent, send a Prowl message
            elif(idleMode and "EXISTS" in line):
                emailId = line.split(" ")[1]
                
                if(emailId not in previousId):
                    previousId = emailId
                    self.fetchEmail(emailId)
                    
            
            line = self.p.stdout.readline()
                    
    def keepAlive(self):
        """Keep the connection from timing out by toggling
        IDLE mode on/off."""
        self.p.stdin.write("DONE\n")
        self.p.stdin.write(". idle\n")
        
        import threading
        self.timer = threading.Timer(timeOutInterval, self.keepAlive)
        self.timer.start()
        
    def stop(self):
        """Kill the timer thread."""
        self.timer.cancel()
        import os
        import signal
        os.kill(self.p.pid, signal.SIGTERM)
          
    def fetchEmail(self, emailId):
        """Grab the email's information and send a Prowl message."""
        global cmd
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        unseenEmail = False
        date = sender = subject = body = ""
        global username, password
        line = p.stdout.readline()
        while(line != None):
            # Input credentials
            if("* OK Gimap ready" in line):
                p.stdin.write(". login %s %s\n" % (username, password))
            # Select the INBOX
            elif("authenticated (Success)" in line):
                p.stdin.write(". examine INBOX\n")
            # Make sure the e-mail has not already been viewed.
            elif("INBOX selected. (Success)" in line):
                p.stdin.write(". fetch %s flags\n" % emailId)
                line = p.stdout.readline()
                if("\\Seen" in line):
                    break
                else:
                    unseenEmail = True
                    print "A new message has been received... " + time.strftime("%m-%d-%Y %H:%M:%S")              
            # Extract the email information
            elif(unseenEmail):         
                p.stdin.write(". fetch %s (body[header.fields (from subject)] body[1])\n" % emailId)
                emailInfo = p.stdout.readline()
                
                captureBody = False
                while(". OK Success" not in emailInfo):
                    if(captureBody):
                        body += emailInfo
                    elif("Subject:" in emailInfo):
                        subject = emailInfo.strip()                
                    elif("From:" in emailInfo):
                        sender = self.removeEmailAddress(emailInfo).strip()
                        
                    if("BODY[1]" in emailInfo):
                        captureBody = True
                        
                    emailInfo = p.stdout.readline()
                      
                break
            
            line = p.stdout.readline()
        
        # Kill the subprocess
        import os
        import signal
        os.kill(p.pid, signal.SIGTERM)
           
        if(unseenEmail): 
            # Grab the current system time
            date = time.strftime("%l:%M %p %a, %b %d, %y").strip()
        
            global bodyLength
            # If the body is longer than the maximum length (1000 chars)
            # add an elipses to the end.
            # Else remove the ")" character from the end.
            if(len(body) > bodyLength):
                body = body[:bodyLength] + "..."
            else:
                body = body[:-3]
        
            self.sendProwlMessage("%s\n%s\n%s\n%s" % (date, sender, subject, body))
    
    def removeEmailAddress(self, email):
        """Removes the email address from the FROM field."""
        pos = email.find(" <")
        
        return email[:pos].replace('\"', '')
        
    def sendProwlMessage(self, message):
        """Send a message using the Prowl API"""
        import urllib
        import httplib
        global apiKey, priority
        data = urllib.urlencode({'apikey': apiKey, 'event': "Gmail", 'application': "Gprowl", 'priority': priority, 'description': message})
        headers = {"Content-type": "application/x-www-form-urlencoded",
        'User-Agent': "Gprowl/%s" % str(__version__)}

        global prowlUrl
        conn = httplib.HTTPSConnection(prowlUrl)
        conn.request("POST", "/publicapi/add", data, headers)
        response = conn.getresponse()
        data = response.read()
        
        if("success" in data):
            print "The notification was successfully delivered."
        else:
            print "The notification was not delivered."
            print data

        conn.close()
        
def usage():
    """Prints the usage."""
    print __doc__
    
def main(argv):
    """Parses the arguments and starts the program."""
    
    global apiKey, username, password, openssl, priority, bodyLength
    
    try:
        opts, args = getopt.getopt(argv, "hl:a:u:p:r:b:", ["help","location=","api=","username=","password=", "priority=", "bodyLength="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-l", "--location"):
            openssl = arg
        elif opt in ("-a", "--api"):
            apiKey = arg
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-r", "--priority"):
            p = int(arg)
            if((p >= -2) and (p <= 2)):
                priority = p
            else:
                print "Invalid Prowl message priority value."
                print "The priority value must be between -2 and 2."
                sys.exit(1)
        elif opt in ("-b", "--bodyLength"):
            b = int(arg)
            if((b >= 0) and (b <= 1000)):
                bodyLength = b
            else:
                print "Invalid Prowl body length value."
                print "The body length value must be between 0 and 1000."
                sys.exit(1)
            
    print "Starting Gprowl Notifier"
    gprowl = GmailIdleNotifier()
    try:
        gprowl.start()
    except KeyboardInterrupt:
        print "\nStopping Gprowl..."
        gprowl.stop()
        sys.exit(0)   
    
if __name__ == "__main__":
    main(sys.argv[1:])
