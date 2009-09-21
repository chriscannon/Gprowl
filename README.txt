Gprowl by Christopher T. Cannon (christophertcannon@gmail.com)

Description:
Gprowl connects to Gmail in IMAP's IDLE mode and pushes new messages to
the user's iPhone with the Prowl iPhone application. This program was
created out of the lack of stable solutions currently available.

Requirements:
* Server:
   * Python version 2.5.2 or greater
   * OpenSSL version 0.9.8j or greater
* iPhone:
   * Prowl

Upcoming features:
* Verify Gmail credentials and Prowl API key.
   - ADDED v0.9

Current bugs:
1. Python crashes when using strptime in a thread.
   OS: Mac OS X 10.6.1 (Snow Leopard)
   Python: 2.5.2 or 2.5.4
   * FIXED v0.9
