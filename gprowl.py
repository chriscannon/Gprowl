#!/usr/bin/env python
"""Push Gmail Prowl Notifier

Connects to Gmail using IMAP's IDLE mode and sends messages
over Prowl to an iPhone.

Usage: python gprowl.py [options]

Options:
    -h, --help              show this help
    -l ..., --location=...  Location of openssl
    
Example:
    gprowl.py -l /usr/bin/openssl
"""

__author__ = "Christopher T. Cannon (christophertcannon@gmail.com)"
__version__ = "0.5"
__date__ = "2009/09/20"
__copyright__ = "Copyright (c) 2009 Christopher T. Cannon"

import sys
import subprocess
import getopt
from threading import Thread
import time

# Prowl API Key
apiKey = ""
# Prowl API URL
prowlUrl = "prowl.weks.net"
# Gmail user name
username = ""
# Gmail password
password = ""
# openssl location
openssl = "/usr/bin/openssl"
# IMAP connection command
cmd = [openssl, "s_client", "-connect", "imap.gmail.com:993", "-crlf"]


class GmailIdleNotifier:
    def __init__(self):
        self.getProwlApiKey()
        self.getGmailCredentials()
    
    def getProwlApiKey(self):
        """Promt the user and verify their Prowl API key."""
        global apiKey
        apiKey = raw_input("Prowl API key: ")         
        
    def getGmailCredentials(self):
        """Prompt the user and verify their Gmail credentials."""
        global username, password
        username = raw_input("Gmail User Name: ")
        
        import getpass
        password = getpass.getpass("Gmail Password: ")
    
    def start(self):
        """Log into the Google IMAP server and enable IDLE mode."""
        global cmd
        # Start the openssl process
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        idleMode = False
        previousId = ""
        global username, password
        line = p.stdout.readline()
        while(line != None):
            # Input the credentials
            if("* OK Gimap ready" in line):
                p.stdin.write(". login %s %s\n" % (username, password))
            # Select the INBOX
            elif("authenticated (Success)" in line):
                print "Successful authentication..."
                p.stdin.write(". examine INBOX\n")
            # Start IDLE mode
            elif("INBOX selected. (Success)" in line):
                p.stdin.write(". idle\n")
                idleMode = True
                print "Now in IMAP IDLE mode..."
            # If IDLE mode is True and the email ID was not
            # previously sent, send a Prowl message
            elif(idleMode and "EXISTS" in line):
                emailId = line.split(" ")[1]
                if(emailId not in previousId):
                    print "A new message has been received..."
                    f = FetchEmailThread(emailId)
                    previousId = emailId
    
            line = p.stdout.readline()

class FetchEmailThread(Thread):
    def __init__(self, emailId):
        Thread.__init__(self)
        self.emailId = emailId
        self.start()
          
    def run(self):
        """Grab the email's information and send a Prowl message."""
        global cmd
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        date = sender = subject = ""
        global username, password
        line = p.stdout.readline()
        while(line != None):
            # Input credentials
            if("* OK Gimap ready" in line):
                p.stdin.write(". login %s %s\n" % (username, password))
            # Select the INBOX
            elif("authenticated (Success)" in line):
                p.stdin.write(". examine INBOX\n")
            # Extract the email information
            elif("INBOX selected. (Success)" in line):         
                p.stdin.write(". fetch %s (body[header.fields (from subject date)])\n" % self.emailId)
                p.stdout.readline()
                
                for i in range(0,3):
                    emailInfo = p.stdout.readline()
                    if("Subject:" in emailInfo):
                        subject = emailInfo.strip()
                    elif("Date:" in emailInfo):
                        date = self.formatDate(emailInfo).strip()
                    elif("From:" in emailInfo):
                        sender = self.removeEmailAddress(emailInfo).strip()   
                break
            
            line = p.stdout.readline()
        
        # Kill the subprocess
        import os
        import signal
        os.kill(p.pid, signal.SIGTERM)
            
        self.sendProwlMessage("Date: %s\n%s\n%s" % (date, sender, subject))
        
    def formatDate(self,date):
        """Returns a more human-readable format of the email's date."""    
        end = 0
        if("-" in date):
            end = date.rfind("-")
        else:
            end = date.rfind("+")

        t = time.strptime(str(date[6:end]).strip(),"%a, %d %b %Y %H:%M:%S")
        t = time.strftime("%I:%M %p %a, %d %b")
        
        return t
    
    def removeEmailAddress(self, email):
        """Removes the email address from the FROM field."""
        pos = email.find(" <")
        
        return email[:pos]
        
    def sendProwlMessage(self, message):
        """Send a message using the Prowl API"""
        import urllib
        import httplib
        global apiKey
        data = urllib.urlencode({'apikey': apiKey, 'event': "Gmail", 'application': "Gprowl", 'description': message})
        headers = {"Content-type": "application/x-www-form-urlencoded",
        'User-Agent': "Gprowl/%s" % str(__version__)}

        global prowlUrl
        conn = httplib.HTTPSConnection(prowlUrl)
        conn.request("POST", "/publicapi/add", data, headers)
        response = conn.getresponse()

        conn.close()
        
def usage():
    """Prints the usage."""
    print __doc__
    
def main(argv):
    """Parses the arguments and starts the program."""
    
    global apiKey, username, password, openssl
    
    try:
        opts, args = getopt.getopt(argv, "hl:", ["help","location="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-l", "--location"):
            openssl = arg
            
    print "Starting Gprowl Notifier"
    GmailIdleNotifier().start()
    
    
if __name__ == "__main__":
    main(sys.argv[1:])
