#!/usr/bin/env python
"""Gprowl

A Python script that connects to Gmail in IMAP's IDLE mode and pushes new messages to an iPhone using Prowl.

Requirements:
    Python 2.5 or greater
    OpenSSL 0.9.8j or greater
    Prowl iPhone application
    
Usage: python gprowl.py [options]

Options:
    -h, --help              show this help
    -a ..., --api=...       Prowl API key
    -u ..., --username=...  Gmail username
    -p ..., --password=...  Gmail password
    -l ..., --location=...  Location of openssl
    
Example:
    gprowl.py -l /usr/bin/openssl
"""

__author__ = "Christopher T. Cannon (christophertcannon@gmail.com)"
__version__ = "0.9.1"
__date__ = "2009/09/22"
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
        self.checkConnection()
        if(len(apiKey) == 0):
            self.getProwlApiKey()
        if((len(username) == 0) or (len(password) == 0)):
            self.getGmailCredentials()
    
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
                     
        
    def getGmailCredentials(self):
        """Prompt the user and verify their Gmail credentials."""
        global username, password
        
        import getpass
        loop = True
        while(loop):
            uname = raw_input("Gmail User Name: ")
            passwd = getpass.getpass("Gmail Password: ")
            
            if(not uname.endswith("@gmail.com")):
                print "Please append @gmail.com to the user name."
            else:
                global cmd
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                line = p.stdout.readline()
                while(line != None):
                    # Input the credentials
                    if("* OK Gimap ready" in line):
                        p.stdin.write(". login %s %s\n" % (uname, passwd))
                    # Credentials are valid
                    elif("authenticated (Success)" in line):
                        loop = False
                        username = uname
                        password = passwd
                        break
                    elif("Invalid credentials" in line):
                        print "The Gmail username or password entered is invalid."
                        print "Please re-enter the Gmail username and password."
                        break
                    
                    line = p.stdout.readline()
                
                # Kill the subprocess
                import os
                import signal
                os.kill(p.pid, signal.SIGTERM)
            
    
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
            # Invalid command line credentials
            elif("Invalid credentials" in line):
                print "Invalid Gmail credentials..."
                sys.exit(1)
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
                    print "A new message has been received... " + time.strftime("%m-%d-%Y %H:%M:%S")
                    
                    self.fetchEmail(emailId)
                    previousId = emailId
    
            line = p.stdout.readline()
          
    def fetchEmail(self, emailId):
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
                p.stdin.write(". fetch %s (body[header.fields (from subject date)])\n" % emailId)
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
            
        self.sendProwlMessage("%s\n%s\n%s" % (date, sender, subject))
        
    def formatDate(self,date):
        """Returns a more human-readable format of the email's date."""    
        end = len(date)
        if("-" in date):
            end = date.rfind("-")
        elif("+" in date):
            end = date.rfind("+")
        
        t = None
        if("," in date):
            t = time.strptime(str(date[6:end]).strip(),"%a, %d %b %Y %H:%M:%S")
        else:
            t = time.strptime(str(date[6:end]).strip(),"%d %b %Y %H:%M:%S")
            
        t = time.strftime("%I:%M %p %a, %b %d",t)
        
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
        opts, args = getopt.getopt(argv, "hl:a:u:p:", ["help","location=","api=","username=","password="])
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
            
    print "Starting Gprowl Notifier"
    GmailIdleNotifier().start()
    
if __name__ == "__main__":
    main(sys.argv[1:])
