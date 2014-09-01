#!/usr/bin/python

import pdb
import httplib2
import MySQLdb
import sys
import classFncts as F
import argparse
import os
import time
from multiprocessing import Process, Queue

from datetime import date, datetime

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.oauth import TwoLeggedOAuthCredentials
import apiclient

SLEEPY = 40

OAUTH_CONSUMER_KEY = <YOUR CONSUMER KEY>
OAUTH_CONSUMER_SECRET = <YOUR CONSUMER SECRET>

OAUTH_CONSUMER_KEY_TEST = <YOUR TEST CONSUMER KEY>
OAUTH_CONSUMER_SECRET_TEST = <YOUR TEST CONSUMER SECRET>

######################################
#                                    #
# multiprocess - work gets done here #
#                                    #
######################################
def create_these_cals(db, credentials, instructorUserList, thisTerm, domain, calExists, dstLastYear, dstThisYear, dstNextYear, holidayList, instance, setTrace=False):
  if setTrace: pdb.set_trace()

  rightNow = datetime.now()
  now = rightNow.strftime("%Y%m%d-%H_%M_%S")
  processLog = "blackboardCal%d-%s" % (instance, now)
  logName= "%s.log" % processLog
  logfile = open(logName, 'w')
  logName= "%s.err" % processLog
  errorfile = open(logName, 'w')
  logName = "%s.enc" % processLog
  eventsfile = open(logName, 'w')

  subClasses = db.cursor(MySQLdb.cursors.DictCursor)  # used to grab class information 
  subMeetings = db.cursor(MySQLdb.cursors.DictCursor) # used to grab class meeting information
  subUpdateTable = db.cursor()                        # used to update the database with calendar information
 
  # setting some variables
  entry = ""
  requestor=""
  defaultSummary = "This is the \"Active\" calendar maintained by the instructor for this course. You were automatically "
  defaultSummary = defaultSummary + "subscribed to this calendar when you enrolled in this course. Initial scheduling information was "
  defaultSummary = defaultSummary + "automatically added from the course record in UAonline, and may be changed by the instructor(s) as "
  defaultSummary = defaultSummary + "necessary. The instructor(s) may choose to delete this calendar- or remove your subscription to it- "
  defaultSummary = defaultSummary + "at the end of the term it represents (or at any other time.)"

  # grab all the classes this instructor teaches this term
  for instructorUsername in instructorUserList:
    if setTrace: pdb.set_trace()

    query = """select * from ssr2fcx_courses as class, camp_code as cc
               where class.campusCode = cc.Code and cc.University='UAF' 
               and instructorUsername = "%s" and term=%s""" % (instructorUsername, thisTerm) 
    for i in range(0,5):
      try:
        classLines = subClasses.execute(query)
      except:
        exctype, error = sys.exc_info()[:2]
        errorCode = F.error_code_cleanup(error)
        error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
        errorfile.write(error)
        logfile.write(error)
        print error
        time.sleep(SLEEPY)
        continue
      break

    while True:
      if setTrace: pdb.set_trace()

      classRow = subClasses.fetchone()
      if classRow == None: break
      
      uaUsername = classRow['instructorUsername'].rstrip()

      uaEmail = "%s%s" %(uaUsername, domain)
      print "uaEmail = ", uaEmail

      coCrn = classRow['crn']
      print "coCrn = ", coCrn

      if (coCrn not in calExists):  #  Don't create the calendar if it already exists
        entry = "calendar coCrn = %s does not yet exist\n" % coCrn

        if(uaEmail != requestor):   #  different owner than last iteration
          entry = "new calendar owner - uaEmail = %s, requestor = %s" % (uaEmail, requestor)
          print entry
          entry = "%s\n" % entry
          logfile.write(entry)
          requestor = uaEmail
          credentials.requestor = requestor  # create / build connection

          #######################################################
          # Build a service object for interacting with the API #
          #######################################################
          credentials.requestor = requestor
          (entry, service) = F.return_service(credentials.requestor, credentials)
          if (entry == ""):
            # success
            entry = 'service successfully created'
            print entry
            logfile.write('%r\n' % (entry))
          else:
            print entry
            logfile.write(entry)
            errorfile.write(entry)
            continue # no reason to keep going if connection hasn't been made

        #########################
        # connection successful #
        #########################
        title = "%s %s %s - %s" % (classRow['subjectDesc'], classRow['courseNum'], classRow['sequenceNum'], thisTerm)
        summary = "CRN %s: %s" % (classRow['crn'], defaultSummary)

        (entry, calId) = F.create_cal(thisTerm, coCrn, title, summary, service)
        if ("LIMIT" in entry):
          error = entry + "Quiting program Daily Limit Reached\n"
          print error
          errorfile.write(error)
          logfile.write(error)
          print "instance #%s returning" % instance

          eventsfile.close()
          errorfile.close()
          logfile.close()

          subClasses.close
          subMeetings.close
          subUpdateTable.close

          return
        elif (calId == "FAILED"):  # calendar creation failed
          error = "ERROR: %s - Calendar creation Failed, entry = %s\n" % (coCrn, entry)
          print error
          errorfile.write(error)
          continue  # no reason to proceed if no calendar was created to add events to
        else:
          print "  ", entry
          logfile.write(entry)
          calExists[coCrn] = "exists"

        # create events
        query = """select * from ssr2fcx_meeting where term = %s AND crn = %s""" % (thisTerm, coCrn)
        for i in range(0,5):
          try:
            meet = subMeetings.execute(query)
          except:
            exctype, error = sys.exc_info()[:2]
            errorCode = F.error_code_cleanup(error)
            error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
            errorfile.write(error)
            logfile.write(error)
            print error
            time.sleep(SLEEPY)
            continue
          break

        # loop through class meeting information query
        while True:
          meetRow = subMeetings.fetchone()
          if meetRow == None: break

          meetInfo = "%s %s %s, %s, %s" % (classRow['subjectDesc'], classRow['courseNum'], classRow['sequenceNum'], thisTerm, coCrn)
          (entry, eventID) = F.create_event(meetRow, meetInfo, service, calId, dstLastYear, dstThisYear, dstNextYear)

          if ("LIMIT" in entry):
            error = entry + "Quiting program Daily Limit Reached\n"
            print error
            errorfile.write(error)
            logfile.write(entry)

            eventsfile.close()
            errorfile.close()
            logfile.close()

            subClasses.close
            subMeetings.close
            subUpdateTable.close

            return
          elif ("ERROR" in entry):  # event creation failed
            print entry
            entry = "%s\n" % entry
            logfile.write(entry)
            tempVar = entry.split('= ')
            eventsfile.write(tempVar[1])
            error = "tempVar[1] = %s\n" % tempVar[1]
            print error
            errorfile.write(error)
          else:
            print entry
            logfile.write('%r\n' % (entry))

          # cancel events that occur during holidays (like spring break) 
          if (eventID > ""):
            entry = F.cancel_holiday_classes(holidayList, calId, eventID, service)
            if ('SUCCESS' in entry):
              # success
              entry = "%s\n" % entry
              print entry
              logfile.write(entry)
            else:
              # failure
              entry = "  FAILED to remove classes on holidays. %s\n" % entry
              print entry
              logfile.write(entry)
              errorfile.write(error) 
         
        # insert calendar information into database 
        uQuery = """INSERT into classCalendars SET CRN = '%s', term = '%s', calId = '%s', ownerUsername = '%s'""" % \
                    (coCrn, thisTerm, MySQLdb.escape_string(calId), uaUsername)
        for i in range(0,5):
          try:
            subUpdateTable.execute(uQuery)
          except:
            exctype, error = sys.exc_info()[:2]
            errorCode = F.error_code_cleanup(error)
            error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
            errorfile.write(error)
            logfile.write(error)
            print error
            time.sleep(SLEEPY)
            continue
          break

        db.commit()
      else:
        entry = "calendar = %s already exists" % coCrn
        print entry
        logfile.write(entry)

  subClasses.close
  subMeetings.close
  subUpdateTable.close
  
  print "instance #%s done!" % instance 
 
  eventsfile.close()
  errorfile.close()
  logfile.close()

  return


#################################################################################################################################


if __name__ == '__main__':
  ########################################
  #                                      #
  # command line vars and help responses #
  #                                      #
  ########################################
  parser = argparse.ArgumentParser(description='Live Calendars for use by class during the semester - blackboard learn / bboogle calendars')
  parser.add_argument("term", type=int,
                     help='Should be in the form YYYYSS (four digit year followed by two digit semester code ex. 201201) OR FQ for wintermester')
  parser.add_argument("-t", "--testOrProd", help="PROD or defaults to TEST", default="TEST", metavar = '')
  args = parser.parse_args()

  #############################
  #                           #
  # checking passed arguments #
  #                           #
  #############################
  thisTerm = args.term
  if (thisTerm < 201201):
    print "Term is too small.  Should be in the form YYYYSS (four digit year followed by two digit semester code ex. 201201)"
    sys.exit (1)
  elif (thisTerm > 203303):
    print "Term is too large.  Should be in the form YYYYSS (four digit year followed by two digit semester code ex. 201201)"
    sys.exit (1)

  tempVar = args.testOrProd
  if (tempVar.upper() == "TEST"):
    useAcct = "TEST"
  elif (tempVar.upper() == "PROD"):
    useAcct = "PROD"
  else:
    print "--testOrProd must be either TEST or PROD - those are your only choices.  TEST is using poc.alaska.edu, PROD uses alaska.edu"
    sys.exit (1)

  ########
  #      #
  # logs #
  #      #
  ########
  rightNow = datetime.now()
  now = rightNow.strftime("%Y%m%d-%H_%M_%S")
  thisFileName = "blackboard-%s" % now
  log = "%s.log" % thisFileName
  loggfile = open(log, 'w')
  log  = "%s.err" % thisFileName
  errfile = open(log, 'w')

  ################################
  #                              #
  # Use Test setup or Prod setup #
  #                              #
  ################################
  if (useAcct == "PROD"):
    entry = "*** USING PROD ACCOUNTS ***\n"
    dbName = "coursefinder"
    credentials = TwoLeggedOAuthCredentials(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, 'UA Class Calendar API Project') 
    domain = "@alaska.edu"
    adminAcct = "cal_admin001@alaska.edu"
    holidayCalId = 'alaska.edu_u58bomp32h9mcm146ganvl7n6g@group.calendar.google.com'
  else:
    entry = "*** USING test ACCOUNTS ***\n"
    dbName = "coursefinder_test"
    credentials = TwoLeggedOAuthCredentials(OAUTH_CONSUMER_KEY_TEST, OAUTH_CONSUMER_SECRET_TEST, 'UA Class Calendar API Project TEST')
    domain = "@poc.alaska.edu"
    adminAcct = "cal_admin001@poc.alaska.edu"
    holidayCalId = 'poc.alaska.edu_qddl0dgc0sm7v6kji8m7s00dc0@group.calendar.google.com'

  print entry
  loggfile.write(entry)

  credentials.requestor = adminAcct
  (entry, service) = F.return_service(credentials.requestor, credentials)
  if (entry == ""):
    # success
    entry = 'service successfully created'
    print entry
    loggfile.write('%r\n' % (entry))
  else:
    print entry
    loggfile.write(entry)
    errfile.write(entry)
    loggfile.close()
    errfile.close()
    sys.exit(error)

  #############################################################################
  #                                                                           #
  # US DST Rules                                                              #
  #                                                                           #
  # This is a simplified (i.e., wrong for a few cases) set of rules for US    #
  # DST start and end times. For a complete and up-to-date set of DST rules   #
  # and timezone definitions, visit the Olson Database (or try pytz):         #
  # http://www.twinsun.com/tz/tz-link.htm                                     #
  # http://sourceforge.net/projects/pytz/ (might not be up-to-date)           #
  #                                                                           #
  # In the US, since 2007, DST starts at 2am (standard time) on the second    #
  # Sunday in March, which is the first Sunday on or after Mar 8.             #
  # and ends at 2am (DST time; 1am standard time) on the first Sunday of Nov. #
  #                                                                           #
  #############################################################################
  dstLastYear={}
  dstThisYear={}
  dstNextYear={}

  todaysDate = date.today()
  thisYear = todaysDate.year
  nextYear = thisYear + 1
  lastYear = thisYear - 1

  dst = datetime(lastYear, 3, 8, 2)
  dstLastYear["start"] = F.first_sunday_on_or_after(dst)
  dst = datetime(lastYear, 11, 1, 1)
  dstLastYear["end"] = F.first_sunday_on_or_after(dst)

  dst = datetime(thisYear, 3, 8, 2)
  dstThisYear["start"] = F.first_sunday_on_or_after(dst)

  dst = datetime(thisYear, 11, 1, 1)
  dstThisYear["end"] = F.first_sunday_on_or_after(dst)

  dst = datetime(nextYear, 3, 8, 2)
  dstNextYear["start"] = F.first_sunday_on_or_after(dst)

  dst = datetime(nextYear, 11, 1, 1)
  dstNextYear["end"] = F.first_sunday_on_or_after(dst)

  entry = "Last year - %s to %s", dstLastYear["start"].strftime("%m/%d/%Y"), dstLastYear["end"].strftime("%m/%d/%Y")
  entry = "This year - %s to %s", dstThisYear["start"].strftime("%m/%d/%Y"), dstThisYear["end"].strftime("%m/%d/%Y")
  entry = "Next year - %s to %s", dstNextYear["start"].strftime("%m/%d/%Y"), dstNextYear["end"].strftime("%m/%d/%Y")

  ################################
  #                              #
  # Get a list of class holidays #
  #                              #
  ################################
  holidayList= []
  (entry, holidayList) = F.return_holidays(holidayCalId, service, thisTerm)
  entry = "holidays = %s\n" % holidayList

  ##########################
  #                        #
  # Database connection    #
  # Two datase connections #
  # One for each Process   #
  #                        #
  ##########################
  try:
    db = MySQLdb.connect(host="rendu.alaska.edu", port=3306, db=dbName, read_default_file="~/.my.cnf")
  except MySQLdb.Error, e:
    entry = "Error %d: %s\n" % (e.args[0], e.args[1])
    loggfile.write(entry)
    errfile.write(entry)
    sys.exit (1)

  try:
    db2 = MySQLdb.connect(host="rendu.alaska.edu", port=3306, db=dbName, read_default_file="~/.my.cnf")
  except MySQLdb.Error, e:
    entry = "Error %d: %s\n" % (e.args[0], e.args[1])
    loggfile.write(entry)  
    errfile.write(entry)
    sys.exit (1)

  classes = db.cursor(MySQLdb.cursors.DictCursor)       # used for grabbing all classes this term
  meetings = db.cursor(MySQLdb.cursors.DictCursor)      # used to grab a list of course meeting times
  updateTable = db.cursor()                             # used for updating database
  sched = db.cursor(MySQLdb.cursors.DictCursor)         # used to grab a list of classes scheduled this term

  #########################
  #                       #
  # Splitting up the work #
  #                       #
  #########################
  query = """select count(distinct(instructorUsername)) as totalCount from ssr2fcx_courses as class, camp_code as cc
             where term  = %s
             and class.campusCode = cc.Code and cc.University='UAF'""" % (thisTerm)
  for i in range(0,5):
    try:
      classesLines = classes.execute(query)
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = F.error_code_cleanup(error)
      error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      errfile.write(error)
      loggfile.write(error)
      print error
      time.sleep(SLEEPY)
      continue
    break

  instructorCount = classes.fetchall()
  instructorCountHalf = instructorCount[0]['totalCount'] / 2;
  instructorCountLeft = instructorCount[0]['totalCount'] - instructorCountHalf

  firstHalf=[]
  query = """select distinct(instructorUsername) as name from ssr2fcx_courses as class, camp_code as cc
             where term = %s and instructorUsername >'' 
             and class.campusCode = cc.Code and cc.University='UAF'
             order by instructorUsername 
             limit %s""" % (thisTerm, instructorCountHalf)

  for i in range(0,5):
    try:
      classesLines = classes.execute(query)
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = F.error_code_cleanup(error)
      error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      errfile.write(error)
      loggfile.write(error)
      print error
      if setTrace: pdb.set_trace()
      continue
    break

  while True:
    nameRow = classes.fetchone()
    if nameRow ==None: break
    firstHalf.append(nameRow['name'])

  secondHalf=[]
  query = """select distinct(instructorUsername) as name from ssr2fcx_courses as class, camp_code as cc
             where term = %s and instructorUsername >''
             and class.campusCode = cc.Code and cc.University='UAF'
             order by instructorUsername desc limit %s""" % (thisTerm, instructorCountLeft)

  for i in range(0,5):
    try:
      classesLines = classes.execute(query)
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = F.error_code_cleanup(error)
      error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      errfile.write(error)
      loggfile.write(entry)
      print error
      if setTrace: pdb.set_trace()
      continue
    break

  while True:
    nameRow = classes.fetchone()
    if nameRow ==None: break
    secondHalf.append(nameRow['name'])

  #######################################################
  #                                                     #
  # grab any calendars that already exist for this term #
  #                                                     #
  #######################################################
  calExists={}
  query ="""select * from classCalendars where term = %s""" % (thisTerm)
  for i in range(0,5):
    try:
      classesLines = classes.execute(query)
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = F.error_code_cleanup(error)
      error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      errfile.write(error)
      loggfile.write(error)
      print error
      if setTrace: pdb.set_trace()
      continue
    break

  while True:
    classesRow = classes.fetchone()
    if classesRow == None: break
    key = classesRow["CRN"]
    calExists[key] = classesRow

  # note: can't use set_trace when using processes
  myProcess1 = Process(target=create_these_cals, args=(db, credentials, firstHalf, thisTerm, domain, calExists, dstLastYear, dstThisYear, dstNextYear, holidayList, 1))
  myProcess1.start()
  myProcess2 = Process(target=create_these_cals, args=(db2, credentials, secondHalf, thisTerm, domain, calExists, dstLastYear, dstThisYear, dstNextYear, holidayList, 2))
  myProcess2.start()

  entry = "All process started"
  print entry
  loggfile.write(entry)

  myProcess1.join()
  myProcess2.join()

  print "both processes should be done!"

  ##################################################################################
  #                                                                                #
  # build the connection with the admin acct since there is no course owner listed #
  #                                                                                #
  ##################################################################################
  requestor = adminAcct  # create / build connection
  if (credentials.requestor != adminAcct):
    credentials.requestor = requestor
    (entry, service) = F.return_service(credentials.requestor, credentials)
    if (entry == ""):
      # success
      entry = 'service successfully created'
      print entry
      loggfile.write('%r\n' % (entry))
    else:
      print entry
      loggfile.write(entry)
      errfile.write(entry)

      loggfile.close()
      errfile.close()

      meetings.close
      updateTable.close
      classes.close
      sched.close
      db.close
      sys.exit(error)

  defaultSummary = "This is the \"Active\" calendar maintained by the instructor for this course. You were automatically "
  defaultSummary = defaultSummary + "subscribed to this calendar when you enrolled in this course. Initial scheduling information was "
  defaultSummary = defaultSummary + "automatically added from the course record in UAonline, and may be changed by the instructor(s) as "
  defaultSummary = defaultSummary + "necessary. The instructor(s) may choose to delete this calendar- or remove your subscription to it- "
  defaultSummary = defaultSummary + "at the end of the term it represents (or at any other time.)"

  ##############################################################
  #                                                            #
  # Now grab all courses from sched that don't have a calendar #
  # These will have to be created with the default calendar    #
  # owner account since there was no listed good owner         #
  #                                                            #
  ##############################################################
  debug = ""
  query = """select * from camp_code as cc, ssr2fcx_courses as sched
             left outer join classCalendars on sched.crn = classCalendars.CRN AND sched.term = classCalendars.term
             where classCalendars.id is null AND sched.term = %s
             and sched.campusCode = cc.Code and cc.University='UAF' %s""" % (thisTerm, debug)

  for i in range(0,5):
    try:
      sched.execute(query)
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = F.error_code_cleanup(error)
      error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      errfile.write(error)
      print error
      continue
    break

  while True:
    schedDbRow = sched.fetchone()
    if schedDbRow == None: break 
  
    # create calendar
    entry = "Calendar Creation Process part2 for crn = %s, account = %s\n" % (schedDbRow['crn'], adminAcct)
    print entry
    loggfile.write(entry)

    courseName = "%s %s %s" % (schedDbRow['subjectCode'], schedDbRow['courseNum'], schedDbRow['sequenceNum'])
    title = "%s - %s" % (courseName, thisTerm)
    summary = "CRN %s: %s" % (courseName, defaultSummary)

    (entry, calId) = F.create_cal(thisTerm, schedDbRow['crn'], title, summary, service)
    if ("LIMIT" in entry):
      error = entry + "Quiting program Daily Limit Reached\n"
      print error
      errfile.write(entry)

      loggfile.close()
      errfile.close()

      meetings.close
      updateTable.close
      classes.close
      sched.close
      db.close
      sys.exit(error)
    elif (calId == "FAILED"):  # calendar creation failed
      error = "ERROR: %s - Calendar creation Failed, entry = %s\n" % (schedDbRow['crn'], entry)
      print error
      errfile.write(error)
      loggfile.write(error)
      continue  # no reason to continue if no calendar was created to add events to
    else:
      print "  ", entry
      loggfile.write(entry)

    # create events
    query = """select * from ssr2fcx_meeting where term = %s AND crn = %s""" % (thisTerm, schedDbRow['crn'])
    for i in range(0,5):
      try:
        meet = meetings.execute(query)
      except:
        exctype, error = sys.exc_info()[:2]
        errorCode = F.error_code_cleanup(error)
        error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
        errfile.write(error)
        loggfile.write(error)
        print error
        continue
      break
    
    # loop through meet query
    while True:
      meetRow = meetings.fetchone()
      if meetRow == None: break

      # create events
      meetInfo = "%s, %s, %s" % (courseName, thisTerm, schedDbRow['crn'])
      (entry, eventID) = F.create_event(meetRow, meetInfo, service, calId, dstLastYear, dstThisYear, dstNextYear)

      if ("LIMIT" in entry):
        error = entry + "Quiting program Daily Limit Reached\n"
        print error
        errfile.write(error)
        loggfile.write(error)

        loggfile.close()
        errfile.close()

        meetings.close
        updateTable.close
        sched.close
        classes.close
        db.close
        sys.exit(error)
      elif ("ERROR" in entry):  # event creation failed
        print entry
        tempVar = entry.split('= ')
        error = "tempVar[1] = %s\n" % tempVar[1]
        print error
        loggfile.write(error)
        errfile.write(error)
      else:
        print entry
        loggfile.write(entry)

      if (eventID > ""):
        entry = F.cancel_holiday_classes(holidayList, calId, eventID, service)
        if ('SUCCESS' in entry):
          # success
          entry = "%s\n" % entry
          print entry
          loggfile.write(entry)
        else:
          # failure
          entry = "  FAILED to remove classes on holidays. %s\n" % entry
          print entry
          loggfile.write(entry)
          errfile.write(entry)

    # write db entry
    uQuery = """INSERT into classCalendars SET CRN = '%s', term = '%s', calId = '%s', ownerUsername = '%s'""" % \
             (schedDbRow['crn'], thisTerm, MySQLdb.escape_string(calId), "cal_admin001")

    for i in range(0,5):
      try:
        updateTable.execute(uQuery)
      except:
        exctype, error = sys.exc_info()[:2]
        errorCode = F.error_code_cleanup(error)
        error = "** MySQL error => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
        errfile.write(error)
        loggfile.write(error)
        print error
        continue
      break

    db.commit()

  loggfile.close()
  errfile.close()

  meetings.close
  updateTable.close
  sched.close
  classes.close
  db.close
