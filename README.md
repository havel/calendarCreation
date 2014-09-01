Planning Calendar Creation Tool
========================


planningCalendars.py


## What it does:
Every morning about 15,970 course records are reviewed to see if a course is new, altered or no longer exists.  This information is then turned into a public Google Calendar that can be used by students planning their course schedule.  These calendars are connected to the Universities course search web interface as well.


The University of Alaska (UA) uses Google Apps for Education’s suite of tools, which include the infrastructure components email and calendar.   This functionality is available for students, staff and faculty at the University.


Students at the University of Alaska need to be able to look at calendars of courses to see how they all fit together easily.  Calendars are created for every course that has scheduled events.  Course schedules are often changed, especially during the beginning of a semester when class enrollment is very fluid, and these schedules need to be updated regularly.  This accomplished through the Planning Calendar project, which consists of python code that is run nightly.


The University of Alaska has three major academic units, University of Alaska Anchorage, University of Alaska Fairbanks and University of Alaska Southeast.  All three major academic units encompass approximately 33,000 students and 2,500 faculty members.  Additionally UA has a non-academic unit that does common business tasks for three academic units which is named the University of Alaska Statewide.


In bbCal.py I use process for multiprocessing, but because of Google limits the number of requests that can be performed during a period time, the planning calendar code often runs faster than they allow, making no point to multiprocessing.


## Features:
* Ability to run off and update test or production data
* Updates existing calendars with altered meeting information


## Requirements:
* httplib2-0.7.2
* argparse-1.2.1
* google-api-python-client-1.0beta7
* MySQLdb 1.2.3c1


The database table expectations are located in the database.txt file.


Course Calendars
==============


courseCalendars.py


## Overview:
The University of Alaska Fairbanks academic unit automatically creates class calendars that are owned by the individual teaching the class or an administrative account if there is no one listed.  This calendar gets created even if no events are scheduled (such as a thesis or distance at your own schedule class.)  This program is run the first day of the semester manually.


## Requirements:
* httplib2-0.7.2
* argparse-1.2.1
* google-api-python-client-1.0beta7
* MySQLdb 1.2.3c1
* multiprocessing '0.70a1


The database table expectations are located in the database.txt file.


## Settings contained within courseCalendars.py and planningCalendars.py:
* ```OAUTH_CONSUMER_KEY_TEST```  - This string is the Consumer Key for the test account you want to use.  This is found on the Google Developers Console (https://console.developers.google.com/project), after a project has been created.  Located under APIs & auth -> Credentials.  Copy the content found in the test client id.


 * ```OAUTH_CONSUMER_SECRET_TEST``` - This string is the Consumer Secret for the test account you want to use.  This is found on the Google Developers Console (https://console.developers.google.com/project), after a project has been created.  Located under APIs & auth -> Credentials.  Copy the content found in the test client secret.


 * ```OAUTH_CONSUMER_KEY``` - This string is the Consumer Key for the production account you want to use.  This is found on the Google Developers Console (https://console.developers.google.com/project), after a project has been created.  Located under APIs & auth -> Credentials.  Copy the content found in the production client id.


 * ```OAUTH_CONSUMER_SECRET``` - This string is the Consumer Secret for the production account you want to use.  This is found on the Google Developers Console (https://console.developers.google.com/project), after a project has been created.  Located under APIs & auth -> Credentials.  Copy the content found in the production client secret.


Other Settings:
* ```dbName = "coursefinder"``` - Replace coursefinder in both of these strings to the appropriate database.  There is an area for setting this variable to the test value or the production.


* ```credentials.requestor = 'cal_admin001@alaska.edu'``` - Replace both of these email strings to the appropriate account that has administrator rights to the Google domain.


* ```domain = "@alaska.edu"``` - Replace both of these strings to the appropriate domains.


* ```adminAcct = "cal_admin001@alaska.edu"``` - Replace both of these email strings to the appropriate administrative accounts.  This is the account that if an appropriate subject account cannot be used to create or alter the calendar will be used.


* ```db = MySQLdb.connect(host=<MYSQL SERVER HOST>, port=3306, db=dbName, read_default_file="~/.my.cnf")``` - This is the connection string for the database and is assuming you have a mySQL .my.cnf file setup with your username and password.




Shared Functions
======================================


classFncts.py


## Overview:
These are shared functions for common things done with calendars.  More for this file can be found in sharedFunctions.txt.
