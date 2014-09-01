#!/usr/bin/python

import pdb
import httplib2
import MySQLdb
import sys
import classFncts as F

from datetime import date, datetime
import time
import argparse

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.oauth import TwoLeggedOAuthCredentials

OAUTH_CONSUMER_KEY = <YOUR CONSUMER KEY>
OAUTH_CONSUMER_SECRET = <YOUR CONSUMER SECRET>

OAUTH_CONSUMER_KEY_TEST = <YOUR TEST CONSUMER KEY>
OAUTH_CONSUMER_SECRET_TEST = <YOUR TEST CONSUMER SECRET>

#####################################################
# service_check - used to do service error checking #
#####################################################
def service_check(entry, adminAcctOwned, k):
  if (DEBUG): print "got to service check, entry = %s, adminAcctOwned, k = %s" % (entry, k)

  subjectAcct = "VALID"

  if ("INVALID" in entry):
    # acct is invalid 
    if (k in adminAcctOwned):
      error = "ERROR - service check - service not created, already in adminAcctOwned list.  k = %s, error = %s" % (k, entry)
      print error
      logfile.write(error)
      errorfile.write(error)
      subjectAcct = "continue"
    else:
      # move all in subject to admin entry
      adminAcctOwned.append(k)
      subjectAcct = "INVALID"
  elif("ERROR" in entry):
    error = "ERROR: service check - service not created - regarding k = %s because of Error = %s" % (k, entry)
    print error
    logfile.write(error)
    errorfile.write(error)
    subjectAcct = "continue"
  return subjectAcct

#################################################
# event_check - used to do event error checking #
#################################################
def event_check(entry, adminAcctOwned, thisArray, action, acctCredentials, k):
  if (DEBUG): print "  Got to event check, entry = %s, adminAcctOwned, thisArray, action = %s, acctCredentials = %s, k = %s" % (entry, action, acctCredentials, k)

  tempEntry=""

  returnValue = "WTF"

  if (action == "changedRemove"):
    # existing calendar - meetings changed, removing events
    errorSegment = "  Removing events from changed calendar "
  elif (action == "changedAdd"):
    # existing calendar - meetings changed, adding events
    errorSegment = "  Adding events to changed calendar "
  elif (action == "new"):
    errorSegment = "  Creating a new calendar "
  elif (action == "deleted"):
    errorSegment = "  Deleting calendar "

  if ("INVALID" in entry):
    tempEntry = "  %s, credentials failed for %s" % (errorSegment, acctCredentials)
    if (DEBUG): print tempEntry
    logfile.write("%s\n" % (tempEntry))
    if (k not in adminAcctOwned): 
      adminAcctOwned.append(k)
      if (DEBUG): print "  check event - 1 - adminAcctOwned - invalid"
      if (k in thisArray):
        thisArray.remove(k)
      returnValue = "continue"
    else:
      if (DEBUG): print "check event - 1 - adminAcct Invalid"
      adminAcctOwned.remove(k)
      returnValue = "failed" 
  elif ("FORBIDDEN" in entry):
    tempEntry = "  %s, credentials forbidden for %s" % (errorSegment, acctCredentials)
    if (DEBUG): print tempEntry
    logfile.write("%s\n" % (tempEntry))
    if (k not in adminAcctOwned):
      adminAcctOwned.append(k)
      if (DEBUG): print "check event - appeneded to adminAcctOwned"
      if (k in thisArray): 
        thisArray.remove(k)
      if (DEBUG): print "check event - forbidden access, adding it to the adminAcctOwned list for another try"
      returnValue = "failed"
    elif ("cal_admin" in acctCredentials):
      if (DEBUG): print "check event - adminAcct Invalid - don't know who ownes this calendar"
      adminAcctOwned.remove(k)
      returnValue = "failed"
    else:
      if (DEBUG): print "check event - already in adminAcctOwned and not currently credentials of calAdmin"
      returnValue = "failed"
  elif ("LIMIT" in entry or "usage limits exceeded" in entry):
    error = entry + "Quiting program Daily Limit Reached\n"
    print error
    errorfile.write(error)
    logfile.write(error)
    returnValue = "exit"  
  elif ("FAILED" in entry):
    error = "  ERROR: %s FAILED for k = %s" % (errorSegment, k) 
    print error
    errorfile.write("%s\n" % (error))
    print entry
    logfile.write("%s\n" % (entry))
    if (DEBUG): print "  account info => %s requestor = %s" % (errorSegment, acctCredentials)
    returnValue = "failed"
  elif ("UNEXISTANCE" in entry):
    error = "  ERROR: %s - calendar does not exist k = %s, for acct = %s" % (errorSegment, k, acctCredentials)  
    print error
    errorfile.write("%s\n" % (error))
    print entry
    logfile.write("%s\n" % (entry))
    returnValue = "failed"
  elif ("color change was unsuccessful" in entry):
    tempEntry = "  %s, calendar created successfully but with standard color for k = %s" % (errorSegment, k)
    print tempEntry
    logfile.write("%s\n" % (tempEntry))
    returnValue = "success"
  else:
    entry = "  Success %s for k = %s" % (errorSegment, k) 
    print entry
    logfile.write("%s\n" % (entry))
    returnValue = "success"

  if (returnValue == "WTF" and DEBUG): pdb.set_trace()

  return (returnValue, tempEntry, adminAcctOwned, thisArray)

###########################
# updating calendar table #
###########################
def update_calendar_table(updatedCals, cals, useAcct):
  if (DEBUG): print "  update_calendar_table"
  for key in updatedCals:
    (term, crn) = key.split('-')
    owner = cals[key]['owner']
    uQuery = """UPDATE calendar set owner = '%s' where term = %s and crn = %s""" % (owner, term, crn)
    updateTable.execute(uQuery)
    if (DEBUG): print "  successfully updated calendar to owner = %s for term = %s and crn = %s" % (owner, term, crn)
  db.commit()
  if (DEBUG): print " %d calendars owners updated out of %d total calendars" % (len(updatedCals), len(cals))


#####################################
# code for creating calendar by mau #
#####################################                      
def ind_maus(mau, dstLastYear, dstThisYear, dstNextYear, adminAcct, domain, credentials, dbName, logfile, errorfile, alteredLinesSet, db):
  # setting up some variables
  entry = ""
  eventID = ""
  eventsNotCreated = []
  subjectAcct = "VALID"
  toDo = ('changed', 'c-adminAcct', 'new', 'n-adminAcct', 'deleted', 'd-adminAcct')
  service = 'UNDEFINED'
  nextSubject = 0
  oldSubject = ""

  #########################
  #                       #
  # setting up db cursors #
  #                       #
  #########################
  meetings = db.cursor(MySQLdb.cursors.DictCursor) # used for getting information for updated meeting information
  updateTable = db.cursor()                        # used to update the calendar table
  classes = db.cursor(MySQLdb.cursors.DictCursor)  # used to interact with mau classes
  changedOrDeleted = db.cursor()                   # used to check if class schedule was fixed or really deleted

  # class holiday calendars - since we aren't altering them use production accounts
  if (mau == 'uaf'):
    holidayCalId = 'alaska.edu_u58bomp32h9mcm146ganvl7n6g@group.calendar.google.com'
  elif (mau =='uaa'):
    holidayCalId = 'alaska.edu_e7q2937lv8vebkdfoanlrkgvag@group.calendar.google.com'
  else:
    holidayCalId = 'alaska.edu_aul04sss0ncbujpf3hto670sk0@group.calendar.google.com'

  ##########################
  #                        #
  # create holiday listing #
  #                        #
  ##########################
  if DEBUG: print "  creating holiday calendar service"

  # set up a temporary service with production account for holiday calendars, maintaining duplicate calendars for
  # holidays for each mau more trouble than it is worth 
  credentialsHC = TwoLeggedOAuthCredentials(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, 'UA Course Calendar API')
  credentialsHC.requestor = 'cal_admin001@alaska.edu'
  adminAcctHC = "cal_admin001@alaska.edu"
  (entry, serviceHC) = F.return_service(adminAcctHC, credentialsHC)

  if DEBUG: print "  created service entry = ", entry
  if (entry == ""):
    # service successfully created
    (entry, holidayListing) = F.return_holidays(holidayCalId, serviceHC)
  else:
    print entry
    logfile.write("%s\n" % (entry))
    errorfile.write("%s\n" % (entry))
    entry = "  Stopping mau = %s as holiday calendar cannot be queried because of problem listed above." % (mau)
    print entry
    logfile.write("%s\n" % (entry))
    errorfile.write("%s\n" % (entry))
    sys.exit (1) 
 
  if DEBUG: print "  created holiday listing entry = %s for mau = %s" % (entry, mau)

  ####################################################
  #                                                  #
  # grab all mau classes from db and throw in a hash #
  # with (term - crn) being the key                  #
  #                                                  #
  ####################################################
  if DEBUG: print "  creating list of all %s courses" % mau
  majorAU={}
  query="""select crn, term, m.* from ssr2fcx_courses as c
           left join ssr2fcx_meeting as m using (term, crn)
           where campusCode in
                 (select Code from camp_code where University = '%s')
           and m.id is not NULL
           and
           (m.meetStartDate > "20110101" and m.meetEndDate> "20110101" AND m.startTime > "" AND m.endTime>""
            and (m.sunday>"" or m.monday >"" or m.tuesday>"" or m.wednesday>""
            or m.thursday> "" or m.friday > "" or m.saturday >""))""" % mau
  courses = classes.execute(query)
  if DEBUG: print "  finished executing all %s courses query" % mau

  while True:
    mauRow = classes.fetchone()
    if mauRow is None: break
    keyVal = "%s-%s" % (mauRow["term"], mauRow["crn"])  # key value
    majorAU[keyVal] = { 'term':mauRow["term"], 'crn':mauRow["crn"] }
  if DEBUG: print "  put %s courses into dictionary" % mau

  calendarStatus=[]
  changed=[]
  new=[]
  deleted=[]
  adminAcctOwned = []
  updatedOwner = []

  # ssr2fcx -> in new table but not in old, new exactly - changed or new
  # meetOld -> in old table but not in new, deleted
  # calendar -> in new table but not in calendar, missing - new

  ###################################################################
  #                                                                 #
  # altered items - are they new, updated or deleted items          #
  # this is also how keys are set up distinct instead of duplicated #
  #                                                                 #
  ###################################################################
  for index, row in enumerate(alteredLinesSet):
    subject = F.return_subject(row["subjCourseNumSeq"])
    if subject is None:
      print row["subjCourseNumSeq"]
    keyValue = "%s-%s-%s" % (subject, row["term"], row["crn"])  # key value
    testKey = "%s-%s" % (row["term"], row["crn"])

    if (testKey in majorAU):
      if (row["fromTable"] == "calendar"):
        if (keyValue in new or keyValue in deleted): pass
        else:
          new.append(keyValue)
        if (keyValue in changed):
          changed.remove(keyValue)

      elif (row["fromTable"] == "ssr2fcx_meeting"):
        if (keyValue in new): pass
        elif (keyValue in changed): pass
        else: changed.append(keyValue)

        if (keyValue in deleted):
          deleted.remove(keyValue)

      elif (row["fromTable"] == "meetOld"):
        # occassionally (well more often than I like) they remove a meeting time, but the remaining meeting rows are exactly the same
        # so it looks like the class is deleted, but really it isn't.
        query = "select count(*) from ssr2fcx_courses where term = %s and crn=%s" % (row["term"], row["crn"])
        for i in range(0,5):
          try:
            doubleCheckLines = changedOrDeleted.execute(query)
          except:
            time.sleep(10)
            continue
          break

        doubleCheckingRow = changedOrDeleted.fetchone()
        if (doubleCheckingRow is None or doubleCheckingRow[0] == 0):
          if (keyValue in new):
            new.remove(keyValue)
          if (keyValue not in deleted):
            deleted.append(keyValue)
        else:
          changed.append(keyValue)
      else:
        entry = "  While going through the list of altered classes, there was an error.  Term = %s, crn = %s.  Continueing." % (row["term"], row["crn"])
        errorfile.write(entry)
        logfile.write(entry)
        if(DEBUG): print entry, "\n"

  ############################################
  #                                          #
  # going through lists of calendars         #
  # new, changed, deleted                    # 
  # and if they are owned by the admin acct  #
  # depending on the status, the list looped #
  # through is set appropriatly              # 
  # changed, new, deleted, adminAcctOwned    #
  # are each lists                           #
  #                                          #
  ############################################
  for item in toDo:
    if (item == 'changed'): calendarStatus = changed
    elif (item == 'new'): calendarStatus = new
    elif (item == 'deleted'): calendarStatus = deleted
    elif ('adminAcct' in item): calendarStatus = adminAcctOwned
    else: 
      entry = "error what dictionary are working on??? = %s" % item
      errorfile.write(entry)
      logfile.write(entry)
      if (DEBUG): print entry, "\n"

    for k in sorted(calendarStatus):
      if (DEBUG): print "for loop k in sorted toDo[item] = %s - k = %r" % (item, k)

      oldSubject = subject
      (subject, term, crn) = k.split('-')
      if (nextSubject > 0 and subject == oldSubject):
        if (DEBUG): print "  Limit has been reached, so trying to see if next subject also has the same issue.  Old Subject = %s, New Subject = %s" % (oldSubject, subject)
        continue
      elif(nextSubject > 0 and subject != oldSubject):
        nextSubject=0
        if (DEBUG): print "  New Subject reached, set nextSubject = 0"
        entry = "Calendar - item = %s, subject = %s, term = %s and crn = %s" % (item, subject, term, crn)

      print entry
      logfile.write("%s\n" % (entry))

      calKey = "%s-%s" % (term, crn)

      if (calKey not in cals and 'new' not in item and 'n-' not in item and 'd-' not in item and item != 'deleted'):
        # calendar does not exist
        if (DEBUG): print "calendar is not in calendar list, key = %s - skipping to next" % calKey
        new.append(k)
        changed.remove(k)
        continue
      elif('adminAcct' in item or (item == "deleted" and "cal_admin001" in cals[calKey]['owner'] and service != 'UNDEFINED')):
        # connecting using admin account
        if ("cal_admin001" not in credentials.requestor):
          if (DEBUG): print "Changed admin Account - admin account is not the current credentials requestor = %s" % credentials.requestor
          credentials.requestor = adminAcct
          if (DEBUG): print "Changed admin Account - credentials.requestor = %r, credentials = %r" % (credentials.requestor, credentials)
          (entry, service) = F.return_service(credentials.requestor, credentials)
          if (service == "FAILED"):
            subjectAcct = "VALID"
            entry = "Admin Account service creation failed 1, continuing"
            if(DEBUG): print entry
            logfile.write("%s\n" % (entry))
            errorfile.write("%s\n" % (entry))
            continue

          subjectAcct = service_check(entry, adminAcctOwned, k)

          if (subjectAcct == "continue"):
            entry = "service creation failed but not invalid, note and continue on"
            if (DEBUG): print entry
            logfile.write("%s\n" % (entry)) 
            subjectAcct = "VALID"
            continue
          elif (subjectAcct == "INVALID"):
            entry = "This subject account = %s is invalid, skip this account and try again with admin" % credentials.requestor
            if (DEBUG): print entry
            logfile.write("%s\n" % (entry)) 
            adminAcctOwned.append(k)
            continue
      else:
        # connecting via subject account 
        if (DEBUG and calKey in cals): print "in Item else calKey = %s, owner = %s" % (calKey, cals[calKey]['owner'])

        if (calKey in cals and cals[calKey]['owner'] is not None and "cal_admin001" in cals[calKey]['owner'] and item != 'deleted'):
          if (DEBUG): print "calKey exists and is cal_admin"

          if (k not in adminAcctOwned):
            adminAcctOwned.append(k)
            entry = "Admin Account is listed as owner k = %r, calKey = %r" % (k, calKey)
            print entry
            logfile.write("%s\n" % (entry))
          continue
        elif (calKey in cals and cals[calKey]['owner'] != "None" and cals[calKey]['owner'] is not None and cals[calKey]['owner'] != ""):
          if (DEBUG): print "cals owner listed = %s" % cals[calKey]['owner']

          if (cals[calKey]['owner'] != credentials.requestor or service == "UNDEFINED"):
            if (DEBUG): print "cals owner is not the current credentials requestor = %s" % credentials.requestor
            subjectAcct = "VALID"
            credentials.requestor = cals[calKey]['owner']
            (entry, service) = F.return_service(credentials.requestor, credentials)
            if (service == "FAILED"):
              subjectAcct = "VALID"
              if (DEBUG): print "Service creation with calendar owner failed 1 - continuing"
              continue
            subjectAcct = service_check(entry, adminAcctOwned, k)
            if (subjectAcct == "continue"):
              if (DEBUG): print "service creation failed but not invalid, note and continue on"
              subjectAcct = "VALID"
              continue
            elif (subjectAcct == "INVALID"):
              if (DEBUG): print "This subject account = %s is invalid, skip this account and try again with admin" % credentials.requestor
              adminAcctOwned.append(k)
              continue
          elif (subjectAcct == "INVALID"):
            if (DEBUG): print "This subject account = %s is invalid, skip this account and try again with admin acct" % credentials.requestor
            adminAcctOwned.append(k)
            continue
        else: # no owner listed create from subject
          if (DEBUG): print "  no owner listed create from subject"

          subjectAcctOwner = "cal_%s01%s" % (subject.lower(), domain)
          if (subjectAcctOwner != credentials.requestor):
            if (DEBUG): print " subjectAcctOwner = %s, is not the creds = %s" % (subjectAcctOwner, credentials.requestor)

            subjectAcct = "VALID"
            credentials.requestor = subjectAcctOwner
            (entry, service) = F.return_service(credentials.requestor, credentials)
            if (service == "FAILED"):
              subjectAcct = "VALID"
              if (DEBUG): print "Service Creation with subject Account Owner = %s failed" % (subjectAcctOwner)
              continue
            subjectAcct = service_check(entry, adminAcctOwned, k)
            if (subjectAcct == "continue"):
              if (DEBUG): print "subjectAcctOwner - service creation failed but not invalid, note and continue on"
              subjectAcct = "VALID"
              continue
            elif (subjectAcct == "INVALID"):
              if (DEBUG): print "sujectAcctOwner - This subject account = %s is invalid, skip this account and try again with admin" % credentials.requestor
              adminAcctOwned.append(k)
              continue
          elif (subjectAcct == "INVALID"):
            adminAcctOwned.append(k)
            if (DEBUG):
              print "This subject account = %s is invalid, skip this account and try again with admin" % credentials.requestor
            continue

      entry = "  Service created if not new calendar, delete all events from k = %s" % (k)
      print entry
      logfile.write("%s\n" % (entry))

      ##################################################
      # if the item is in the marked for deletion list #
      # delete it                                      #
      ##################################################
      if ('d-' in item or item == 'deleted'):
        entry = F.delete_cal(cals[calKey]["calId"], service)
        (result, error, adminAcctOwned, deleted) = event_check(entry, adminAcctOwned, deleted, "deleted", credentials.requestor, k)
        if (result == "exit"):
          nextSubject=nextSubject+1
          continue

        elif (result == "continue"):
          if (DEBUG): print "delete calendar - adminAcctOwned - continue"
          subjectAcct = "INVALID"
          continue
        elif (result == "failed" and "cal_admin" in credentials.requestor):
          if (DEBUG): print "delete calendar eventcheck failed - cal_admin account should be good - deleted empty owner"
          if (calKey in cals):
            cals[calKey]['owner'] = ""
            updatedOwner.append(calKey)
          continue
        elif (result == "failed" and "cal_admin" not in credentials.requestor):
          if (DEBUG): print "delete calendar eventcheck failed - account should be good - try calAdmin instead"
          if (calKey in cals):
            cals[calKey]['owner'] = adminAcct
            updatedOwner.append(calKey)
          continue
        elif (result == "failed" or result =="forbidden"):
          if (DEBUG): print "delete calendar eventcheck failed - account should be good - deleted"
          continue

      ######################################
      # if it isn't a new calendar         #
      # and it isn't marked for deletion   #
      # which of course only leave changed #
      ######################################           
      elif ('new' not in item and 'n-' not in item):
        print "  removing all events using %s" % credentials.requestor
        entry = F.remove_all_cal_events(cals[calKey]["calId"], service)
        (result, error, adminAcctOwned, changed) = event_check(entry, adminAcctOwned, changed, "changedRemove", credentials.requestor, k)
        if (result == "exit"):
          nextSubject=nextSubject+1
          continue
        elif (result == "continue"):
          if (DEBUG): print "change calendars eventcheck 2 - adminAcctOwned - continue"
          subjectAcct = "INVALID"
          continue
        elif (result == "forbidden"):
          if (DEBUG): print "change calendars eventcheck forbidden - account should be good make note of it - not new"
          if (calKey in cals and 'd-' not in item and "cal_admin" not in credentials.requestor):
            cals[calKey]['owner'] = adminAcct
            updatedOwner.append(calKey)
          elif (result == "failed" and "cal_admin" in credentials.requestor):
            if (calKey in cals):
              cals[calKey]['owner'] = ""
              updatedOwner.append(calKey)
          continue
        elif (result == "failed"):
          if ("cal_admin" not in credentials.requestor and calKey in cals):
            cals[calKey]['owner'] = adminAcct
            updatedOwner.append(calKey)
            if (DEBUG): print "change calendars eventcheck failed - account should be good - not new, putting in list for owner to be updated to Admin"
          elif (calKey in cals and "cal_admin" in credentials.requestor):
            cals[calKey]['owner'] = ""
            updatedOwner.append(calKey)
            if (DEBUG): print " failed - account should be good - not new, updating calendar owner to empty"
          else: 
            entry = "ERROR changed calendars issue with credentials = %s, calkey = %s" % (credentials.requestor, calKey)
            if (DEBUG): print entry
            logfile.write("%s\n" % (entry))
            errorfile.write("%s\n" % (entry))
          continue

        if (item == 'c-adminAcct'):
          if (DEBUG): print "item = %s, removing it from list, k = %s" % (item, k)
          adminAcctOwned.remove(k)

        if (cals[calKey]['owner'] == "None" or cals[calKey]['owner'] is None or cals[calKey]['owner'] == ""):
          cals[calKey]['owner'] = credentials.requestor
          updatedOwner.append(calKey)
          if (DEBUG): print "  updated calendar = %s" % calKey


      if (item == 'changed' or 'c-' in item or item == 'new' or 'n-' in item):
        ##############################################################
        # make sure there is a StartTime - no StartTime, no calendar #
        ##############################################################
        query = """Select sched.subjectCode, meet.subjCourseNumSeq, 
                   meet.meetStartDate, meet.meetEndDate, meet.startTime, meet.endTime, meet.bldg, meet.rm,
                   meet.sunday, meet.monday, meet.tuesday, meet.wednesday, meet.thursday, meet.friday, meet.saturday, meet.id as id, sched.id as schedId
                   From ssr2fcx_meeting as meet, ssr2fcx_courses as sched
                   where meet.crn=%s AND meet.term=%s AND 
                   meet.startTime > '' AND meet.crn = sched.crn AND meet.term = sched.term""" % (crn, term)
        calInfo = "%s, %s" % (term, crn)
        for i in range(0,5):
          try:
            newMeetingsSet = meetings.execute(query)
          except:
            time.sleep(10)
            continue
          break

        #######################
        # create calendar     # 
        # and calendar events #            
        ####################### 
        while True:
          if (DEBUG): print "  on to creating events and calendars"
          meetRow = meetings.fetchone()
          if meetRow is None: break
          if(DEBUG): print "  meetid = %s" % meetRow["id"]

          meetInfo = "%s, %s, %s" % (meetRow["subjCourseNumSeq"], term, crn)

          if (('new' in item or 'n-' in item) and calInfo != ''):
            # create the calendar
            entry = "  first meeting entry for k = %s, term = %s and crn = %s" % (k, term, crn)
            print entry
            logfile.write("%s\n" % (entry))

            title = "P-%s - %s" % (meetRow["subjCourseNumSeq"], term)
            summary = "CRN %s: This course calendar is for planning purposes only.  It is not maintained by the " % crn
            summary = summary + "instructor(s) for this course. Once you register for any course, you will automatically "
            summary = summary + "be subscribed to the 'Active' calendar for that course, which is maintained by the instructor(s)."
            summary = summary + "You may wish to remove this Planning calendar at that time to avoid confusion. This calendar will "
            summary = summary + "be automatically deleted at the end of the term it represents."

            (entry, calId) = F.create_cal(term, crn, title, summary, service)
            (result, error, adminAcctOwned, new) = event_check(entry, adminAcctOwned, new, "changedAdd", credentials.requestor, k)
            if (result == "exit"):
              if (DEBUG): print "creating calendar eventcheck is exit ++1 nextSubject"
              eventID = ""
              nextSubject=nextSubject+1
              continue
            elif (result == "continue"):
              if (DEBUG): print "creating calendar eventcheck is continue - setting subjectAcct to invalid"
              subjectAcct = "INVALID"
              eventID = ""
              break
            elif (result == "failed" or result == "forbidden"):
              if (DEBUG): print "creating calendar eventcheck is failed or forbidden - breaking out"
              eventID = ""
              break

            entry = F.set_permissions(calId, service)
            (result, error, adminAcctOwned, new) = event_check(entry, adminAcctOwned, new, "changedAdd", credentials.requestor, k)
            if (result == "exit"):
              if (DEBUG): print "create calendar, setting permissions is exit - ++1 nextSubject"
              nextSubject=nextSubject+1
              continue
            elif (result == "continue"):
              if (DEBUG): print "create calendar, setting permissions is continue - adminAcctOwned - new, continue - setting subjectAcct to invalid"
              subjectAcct = "INVALID"
              continue
            elif (result == "failed"):
              if (DEBUG): print "create calendar, setting permissions failed - account should be good"
              continue

            #############################################################
            # calendar created now add this information to the database #
            #############################################################
            entry = "  Adding calendar information into database - begin"
            print entry
            logfile.write("%s\n" % (entry))

            schedQuery = """select courseStartDate, courseEndDate from ssr2fcx_courses where crn= '%s' AND term = '%s'""" \
                         % (crn, term)
  
            # occassionally will lose connection to databse, so give it a try and re-connect if necessary
            try:
              schedSet = updateTable.execute(schedQuery)
            except:
              try:
                db = MySQLdb.connect(host="rendu.alaska.edu", port=3306, db=dbName, read_default_file="~/.my.cnf")
              except MySQLdb.Error, e:
                entry = "Error %d: %s\n" % (e.args[0], e.args[1])
                errorfile.write(entry)
                print entry
                sys.exit (1)
              updateTable = db.cursor()
              schedSet = updateTable.execute(schedQuery)

            schedRow = updateTable.fetchone()
            if (schedRow != None):
              if (schedRow[0] is not None and schedRow[1] is not None):
                starting = schedRow[0].strftime("%Y%m%d")
                ending = schedRow[1].strftime("%Y%m%d")
                htmlURL = "https://www.google.com/calendar/embed?src=" + calId + "&ctz=America/Anchorage&mode=AGENDA&dates=%s%%2F%s" % (starting, ending)
              else:
                htmlURL = "https://www.google.com/calendar/embed?src=" + calId + "&ctz=America/Anchorage&mode=AGENDA"

              subscribeURL = "http://www.google.com/calendar/hosted/alaska.edu/render?cid=" + calId
              theClass = meetRow['subjCourseNumSeq']
              (subj, blank1, blank2) = theClass.split(' ')
              theClass = subj.lower()
              subj = theClass.strip()
              owner = credentials.requestor

              uQuery = """INSERT into calendar SET crn = '%s', viewURL = '%s', subscribeURL = '%s', term = '%s', calId = '%s', subj = '%s', owner = '%s'""" % \
                       (crn, MySQLdb.escape_string(htmlURL), MySQLdb.escape_string(subscribeURL), term, MySQLdb.escape_string(calId), MySQLdb.escape_string(subj), owner)

              updateTable.execute(uQuery)
              db.commit()

              entry = "  Adding calendar information into database - end"
              print entry
              logfile.write("%s\n" % (entry))

              temp = "%s-%s" % (term, crn)
              if temp not in cals: cals[temp] = { 'calId': calId, 'owner': credentials.requestor }

          ###################################
          # adding events into the calendar #
          ###################################
          calInfo = ""
          eventID = ""

          (entry, eventID) = F.create_event(meetRow, meetInfo, service, cals[calKey]["calId"], dstLastYear, dstThisYear, dstNextYear)
          if ('new' in item):
            (result, error, adminAcctOwned, new) = event_check(entry, adminAcctOwned, new, "new", credentials.requestor, k)
          elif ('changed' in item):
            (result, error, adminAcctOwned, changed) = event_check(entry, adminAcctOwned, changed, "changedAdd", credentials.requestor, k)

          if (result == "exit"):
            if (DEBUG): print "create event eventcheck returned exit - ++1 on nextSubject"
            nextSubject=nextSubject+1
            continue
          elif (result == "continue"):
            if (DEBUG): print "create event eventcheck returned continue - adminAcctOwned - setting subjectAcct to invalid"
            subjectAcct = "INVALID"
            continue
          elif (result == "failed"):
            if (DEBUG): print "create event eventcheck returned failed - account should be good"
            continue

          #####################################
          # after all the events are created  #
          # delete any that happen on class   #
          # holidays (like spring break week) #
          ##################################### 
          if (eventID > ""):
            entry = F.cancel_holiday_classes(holidayListing, cals[calKey]["calId"], eventID, service)
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

        if (eventID > ""):
          ##################
          # update meetOld #
          ##################
          uQuery = """delete from meetOld where term = %s and crn = %s""" % (term, crn)
          updateTable.execute(uQuery)
          db.commit()

          uQuery = """insert into meetOld select * from ssr2fcx_meeting where term = %s and crn = %s""" % (term, crn)
          updateTable.execute(uQuery)
          db.commit()
          if (DEBUG): print "updated meetOld where term = %s and crn = %s""" % (term, crn)

  update_calendar_table(updatedOwner, cals, useAcct)

  meetings.close
  updateTable.close
  classes.close


#################################################################################################################################


################
#              #
# main program #
#              #
################
if __name__ == '__main__':
 
  ########################################
  #                                      #
  # command line vars and help responses #
  #                                      #
  ########################################
  parser = argparse.ArgumentParser(description='Planning Calendars for use by course finder web app for schedule planning')
  parser.add_argument("pathing", help = "Path where files will be written")
  parser.add_argument("-t", "--testOrProd", help="PROD or defaults to TEST", default="TEST", metavar = '', choices=["PROD", "prod", "Prod", "TEST", "test", "Test"])
  parser.add_argument("-D", "--DEBUG", help="use if you want the extra logging", action="store_true")
  args = parser.parse_args()

  #############################
  #                           #
  # checking passed arguments #
  #                           #
  #############################
  tempVar = args.testOrProd
  if (tempVar.upper() == "TEST"):
    useAcct = "TEST"
  elif (tempVar.upper() == "PROD"):
    useAcct = "PROD"
  else:
    print "--testOrProd must be either TEST or PROD - those are your only choices.  TEST is using poc.alaska.edu, PROD uses alaska.edu"
    sys.exit (1)

  pathing = args.pathing
  if pathing.endswith('/'):
    pathing[:-1]
  
  if (args.DEBUG == True):
    DEBUG = True
  else:
    DEBUG = False

  # setting up logging 
  try: 
    logfile = open(pathing + '/pCal.log', 'w')
    errorfile = open(pathing + '/pCal.err', 'w')
  except:
    exctype, error = sys.exc_info()[:2]
    print "Unable to successfully open files at path %s for writing.  Exiting program.  Errors - %s -- %s" % (pathing, exctype, error)
    sys.exit (1)

  # setting some variables
  entry = ""
  service = 'UNDEFINED'
  
  ################################
  #                              #
  # Use Test setup or Prod setup #
  #                              #
  ################################
  if (useAcct == "PROD"):
    entry = "*** USING PROD ACCOUNTS ***\n"
    dbName = "coursefinder"
    credentials = TwoLeggedOAuthCredentials(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET, 'UA Course Calendar API')
    credentials.requestor = 'cal_admin001@alaska.edu'
    domain = "@alaska.edu"
    adminAcct = "cal_admin001@alaska.edu"
  else:
    entry = "*** USING test ACCOUNTS ***\n"
    dbName = "coursefinder_test"
    credentials = TwoLeggedOAuthCredentials(OAUTH_CONSUMER_KEY_TEST, OAUTH_CONSUMER_SECRET_TEST, 'UA Course Calendar TEST API')
    credentials.requestor = 'cal_admin001@poc.alaska.edu'
    domain = "@poc.alaska.edu"
    adminAcct = "cal_admin001@poc.alaska.edu"

  print entry
  logfile.write("%s" % (entry))

  #######################
  #                     #
  # Database connection #
  #                     #
  #######################
  try:
    db = MySQLdb.connect(host="rendu.alaska.edu", port=3306, db=dbName, read_default_file="~/.my.cnf")
  except MySQLdb.Error, e:
    entry = "Error %d: %s\n" % (e.args[0], e.args[1])
    errorfile.write(entry)
    print entry
    sys.exit (1)

  #########################
  #                       #
  # setting up db cursors #
  #                       #
  #########################
  diffRecords = db.cursor(MySQLdb.cursors.DictCursor)  # used for getting new, updated or removed listing
  calendars = db.cursor(MySQLdb.cursors.DictCursor)    # used for getting all existing calendars

  ######################################################################
  #                                                                    #
  # US DST Rules                                                       #
  #                                                                    #
  # This is a simplified (i.e., wrong for a few cases) set of rules    #
  # for US DST start and end times. For a complete and up-to-date set  #
  # of DST rules and timezone definitions, visit the Olson Database    #
  # (or try pytz): http://www.twinsun.com/tz/tz-link.htm               #
  # http://sourceforge.net/projects/pytz/ (might not be up-to-date)    #
  #                                                                    #
  # In the US, since 2007, DST starts at 2am (standard time) on the    #
  # second Sunday in March, which is the first Sunday on or after Mar  #
  # 8. and ends at 2am (DST time; 1am standard time) on the first      #
  # Sunday of Nov.                                                     #
  #                                                                    #
  ######################################################################
  dstLastYear={}
  dstThisYear={}
  dstNextYear={}
  
  todaysDate = date.today()
  thisYear = todaysDate.year
  nextYear = thisYear +1
  lastYear = thisYear -1
  
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

  print "Last year - %s to %s" % (dstLastYear["start"].strftime("%m/%d/%Y"),dstLastYear["end"].strftime("%m/%d/%Y"))
  print "This year - %s to %s" % (dstThisYear["start"].strftime("%m/%d/%Y"),dstThisYear["end"].strftime("%m/%d/%Y"))
  print "Next year - %s to %s" % (dstNextYear["start"].strftime("%m/%d/%Y"),dstNextYear["end"].strftime("%m/%d/%Y"))

  #########################################################
  #                                                       #
  # grab all calendar entries from db and throw in a hash #
  # with (term - crn) being the key                       #
  #                                                       #
  #########################################################
  if (DEBUG): print "  grabbing all existing calendars"
  cals={}
  query="""select crn, term, owner, calId from calendar"""
  allCalendars = calendars.execute(query)
  if DEBUG: print "  finished executing all existing calendars query"
  
  while True:
    calendarsRow = calendars.fetchone()
    if calendarsRow is None: break
    keyVal = "%s-%s" % (calendarsRow["term"], calendarsRow["crn"])  # key value
    cals[keyVal] = { 'calId':calendarsRow["calId"], 'owner':calendarsRow["owner"] }
  if DEBUG: print "  calendars in dictionary"
  
  ######################################################################
  #                                                                    #
  # find all meeting rows without calendar or calendars that have been #
  # changed                                                            #
  #                                                                    #
  ######################################################################
  # m -> new meet entries, t-> old events not in meet, c -> meet entries without calendar
  if DEBUG:  print "  types of calendars"
  table1 = "meetOld"
  table2 = "calendar"
  
  query = """select m.term, m.crn, m.subjCourseNumSeq, m.meetStartDate,
             m.meetEndDate, m.startTime, m.endTime, m.bldg,
             m.rm, m.sunday, m.monday, m.tuesday, m.wednesday,
             m.thursday, m.friday, m.saturday,
             "ssr2fcx_meeting" as fromTable
             from ssr2fcx_meeting as m left join %s as t
             using (term, crn, subjCourseNumSeq, meetStartDate,
                    meetEndDate, startTime, endTime, bldg, rm, sunday,
                    monday, tuesday, wednesday, thursday, friday,
                    saturday)
             WHERE t.id is NULL
             UNION
             select a.term, a.crn, a.subjCourseNumSeq, a.meetStartDate,
             a.meetEndDate, a.startTime, a.endTime, a.bldg,
             a.rm, a.sunday, a.monday, a.tuesday, a.wednesday,
             a.thursday, a.friday, a.saturday, "meetOld" as fromTable
             from %s as a left join ssr2fcx_meeting as b
             using (term, crn, subjCourseNumSeq, meetStartDate,
                    meetEndDate, startTime, endTime, bldg, rm, sunday,
                    monday, tuesday, wednesday, thursday, friday,
                    saturday)
             WHERE b.id is NULL
             UNION
             select c.term, c.crn, c.subjCourseNumSeq, c.meetStartDate,
             c.meetEndDate, c.startTime, c.endTime, c.bldg,
             c.rm, c.sunday, c.monday, c.tuesday, c.wednesday,
             c.thursday, c.friday, c.saturday, "calendar" as fromTable
             from ssr2fcx_meeting as c left join %s as g
             using (term, crn)
             where g.id is NULL
             ORDER by term desc, crn, fromTable""" % (table1, table1, table2)
  
  alteredLines = diffRecords.execute(query)
  alteredLinesSet = diffRecords.fetchall()
  
  entry = "Records found: %d\n" % diffRecords.rowcount
  print entry
  logfile.write("%s\n" % (entry))

  diffRecords.close
  calendars.close
 
  ######################
  #                    #
  # Loop here with mau #
  #                    #
  ######################
  mauList = ('uaf', 'uaa', 'uas')
  for mau in mauList:
    if DEBUG: "  sending mau = %s" % mau
    ind_maus(mau, dstLastYear, dstThisYear, dstNextYear, adminAcct, domain, credentials, dbName, logfile, errorfile, alteredLinesSet, db)

  logfile.close()
  errorfile.close()

